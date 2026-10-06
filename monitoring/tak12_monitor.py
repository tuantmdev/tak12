#!/usr/bin/env python3
"""Read-only TAK12 growth monitor for GSC, PostHog, and referral results."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import fcntl
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

GSC_CREDENTIALS = Path.home() / ".hermes" / "secrets" / "tak12-gsc-service-account.json"
GSC_SITE = "sc-domain:tak-12.com"
POSTHOG_PROJECT_ID = "504827"
POSTHOG_HOST = "https://us.posthog.com"
REFERRAL_STATS_URL = "https://data.tak12.com/api/services/app/AgentReferral/GetReferralStats"
REFERRAL_AGENT_ID = 210
TAK12_AUTH_URL = (
    "https://id.contuhoc.com/realms/cthsso/protocol/openid-connect/auth"
    "?client_id=school&redirect_uri=https%3A%2F%2Ftak12.com%2Fauth%2Fcallback"
    "&response_type=code&scope=openid"
)
TARGET_URLS = [
    "https://tak-12.com/tak12-cambridge-ket-pet-flyers/",
    "https://tak-12.com/tak12-co-tot-khong/",
]


class ReferralAuthenticationError(RuntimeError):
    """The TAK12 referral session is missing, invalid, or expired."""


class ReferralRefreshError(RuntimeError):
    """The approved browser-based referral-session refresh could not complete."""


def secret_value(
    name: str,
    *,
    prefer_file: bool = False,
    env_file: Path | None = None,
) -> str | None:
    process_value = os.environ.get(name)
    if process_value and not prefer_file:
        return process_value
    env_file = env_file or Path.home() / ".hermes" / ".env"
    if env_file.exists():
        prefix = f"{name}="
        for raw_line in env_file.read_text(errors="replace").splitlines():
            if raw_line.startswith(prefix):
                value = raw_line[len(prefix):].strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                    value = value[1:-1]
                if value:
                    return value
    return process_value or None


def store_secret_value(name: str, value: str, env_file: Path | None = None) -> None:
    """Atomically update one secret while preserving all other .env entries."""
    env_file = env_file or Path.home() / ".hermes" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    lock_path = env_file.with_name(env_file.name + ".tak12.lock")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    temporary: Path | None = None
    try:
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        lines = env_file.read_text(errors="replace").splitlines() if env_file.exists() else []
        prefix = f"{name}="
        updated: list[str] = []
        replaced = False
        for line in lines:
            if line.startswith(prefix):
                updated.append(prefix + value)
                replaced = True
            else:
                updated.append(line)
        if not replaced:
            updated.append(prefix + value)

        temp_fd, temp_name = tempfile.mkstemp(
            prefix=env_file.name + ".tak12.", suffix=".tmp", dir=env_file.parent
        )
        temporary = Path(temp_name)
        with os.fdopen(temp_fd, "w") as stream:
            stream.write("\n".join(updated) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, env_file)
        temporary = None
        env_file.chmod(0o600)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        os.close(lock_fd)


def persist_refreshed_session(value: str) -> None:
    """Persist a refreshed session through the sanitized refresh-failure path."""
    try:
        store_secret_value("TAK12_KC_SESSION", value)
    except OSError as exc:
        raise ReferralRefreshError("TAK12 session persistence failed") from exc


def refresh_referral_session() -> str:
    """Log in through TAK12 SSO, extract the HttpOnly data-site session, and persist it."""
    username = secret_value("TAK12_USERNAME")
    password = secret_value("TAK12_PASSWORD")
    if not username or not password:
        raise ReferralRefreshError("TAK12 login credentials are not available")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ReferralRefreshError("Playwright is required to refresh the TAK12 referral session") from exc

    session: str | None = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(TAK12_AUTH_URL, wait_until="networkidle", timeout=60_000)
            page.locator("input[name=username]").fill(username)
            page.locator("input[name=password]").fill(password)
            page.locator("form").evaluate("(form) => form.requestSubmit()")
            page.wait_for_url("https://tak12.com/**", timeout=60_000)
            page.wait_for_timeout(5_000)
            if not page.url.startswith("https://tak12.com/dashboard"):
                raise ReferralRefreshError("TAK12 SSO did not reach the user dashboard")

            page.goto("https://data.tak12.com/", wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(2_000)
            cookies = context.cookies("https://data.tak12.com/")
            session = next(
                (
                    cookie["value"]
                    for cookie in cookies
                    if cookie["name"] == "kc_session"
                    and cookie["domain"].endswith("data.tak12.com")
                ),
                None,
            )
            browser.close()
    except ReferralRefreshError:
        raise
    except Exception as exc:
        raise ReferralRefreshError(f"TAK12 automatic session refresh failed: {type(exc).__name__}") from exc

    if not session:
        raise ReferralRefreshError("TAK12 automatic session refresh did not receive kc_session")
    persist_refreshed_session(session)
    return session


def gsc_credentials():
    credentials = service_account.Credentials.from_service_account_file(
        GSC_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    credentials.refresh(Request())
    return credentials


def gsc_query(token: str, start: date, end: date, dimensions: list[str] | None = None, row_limit: int = 25000) -> list[dict[str, Any]]:
    url = (
        "https://www.googleapis.com/webmasters/v3/sites/"
        + quote(GSC_SITE, safe="")
        + "/searchAnalytics/query"
    )
    body: dict[str, Any] = {
        "startDate": str(start),
        "endDate": str(end),
        "rowLimit": row_limit,
        "dataState": "final",
    }
    if dimensions:
        body["dimensions"] = dimensions
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=45,
    )
    response.raise_for_status()
    return response.json().get("rows", [])


def aggregate(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "clicks": round(sum(row.get("clicks", 0) for row in rows), 2),
        "impressions": round(sum(row.get("impressions", 0) for row in rows), 2),
    }


def inspect_url(token: str, url: str) -> dict[str, Any]:
    response = requests.post(
        "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
        headers={"Authorization": f"Bearer {token}"},
        json={"inspectionUrl": url, "siteUrl": GSC_SITE},
        timeout=45,
    )
    response.raise_for_status()
    status = response.json().get("inspectionResult", {}).get("indexStatusResult", {})
    return {
        "url": url,
        "verdict": status.get("verdict"),
        "coverage": status.get("coverageState"),
        "indexing_state": status.get("indexingState"),
        "last_crawl": status.get("lastCrawlTime"),
        "crawled_as": status.get("crawledAs"),
    }


def posthog_query(api_key: str, hogql: str) -> dict[str, Any]:
    response = requests.post(
        f"{POSTHOG_HOST}/api/projects/{POSTHOG_PROJECT_ID}/query/",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": {"kind": "HogQLQuery", "query": hogql}},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    return {"columns": payload.get("columns", []), "results": payload.get("results", [])}


def referral_query(session_cookie: str, start: date | None = None, end: date | None = None) -> dict[str, Any]:
    response = requests.post(
        REFERRAL_STATS_URL,
        cookies={"kc_session": session_cookie},
        json={
            "agentId": REFERRAL_AGENT_ID,
            "refCodeFilter": None,
            "fromDate": str(start) if start else None,
            "toDate": str(end) if end else None,
        },
        timeout=45,
        allow_redirects=False,
    )
    if 300 <= response.status_code < 400:
        raise RuntimeError("TAK12 referral API redirect rejected")
    if response.status_code == 401:
        raise ReferralAuthenticationError("TAK12_KC_SESSION is missing, invalid, or expired")
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success") or not isinstance(payload.get("result"), dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
        elif isinstance(error, str):
            if error == "session_expired":
                message = "TAK12 referral session expired"
            else:
                message = payload.get("message") or error
        else:
            message = payload.get("message")
        message = message or "unknown referral API error"
        authentication_message = str(message).lower()
        if (
            error == "session_expired"
            or payload.get("unAuthorizedRequest")
            or "signed out" in authentication_message
            or "session expired" in authentication_message
            or "did not login" in authentication_message
        ):
            raise ReferralAuthenticationError("TAK12 referral authentication failed")
        raise RuntimeError("TAK12 referral API returned an unexpected error")
    return payload["result"]


def collect_referral_stats(
    session_cookie: str | None,
    recent_start: date,
    recent_end: date,
    previous_start: date,
    previous_end: date,
) -> dict[str, dict[str, Any]]:
    """Collect all referral windows, refreshing the SSO session at most once."""
    def query_all(cookie: str) -> dict[str, dict[str, Any]]:
        return {
            "recent": referral_query(cookie, recent_start, recent_end),
            "previous": referral_query(cookie, previous_start, previous_end),
            "all_time": referral_query(cookie),
        }

    if not session_cookie:
        return query_all(refresh_referral_session())
    try:
        return query_all(session_cookie)
    except ReferralAuthenticationError:
        return query_all(refresh_referral_session())


def collect() -> dict[str, Any]:
    credentials = gsc_credentials()
    today = date.today()
    recent_end = today - timedelta(days=3)
    recent_start = recent_end - timedelta(days=6)
    previous_end = recent_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=6)

    recent_daily = gsc_query(credentials.token, recent_start, recent_end, ["date"], 100)
    previous_daily = gsc_query(credentials.token, previous_start, previous_end, ["date"], 100)
    top_queries = gsc_query(credentials.token, recent_start, recent_end, ["query"], 50)
    top_pages = gsc_query(credentials.token, recent_start, recent_end, ["page"], 50)

    posthog_api_key = secret_value("POSTHOG_API_KEY")
    if not posthog_api_key:
        raise RuntimeError("POSTHOG_API_KEY is not available")
    referral_session = secret_value("TAK12_KC_SESSION", prefer_file=True)

    posthog_events = posthog_query(
        posthog_api_key,
        "SELECT event, count() AS total, max(timestamp) AS latest "
        "FROM events WHERE timestamp >= now() - INTERVAL 7 DAY "
        "AND event IN ('$pageview', 'cta_click', 'affiliate_cta_click', 'quiz_started', 'quiz_completed') "
        "GROUP BY event ORDER BY total DESC",
    )
    affiliate_breakdown = posthog_query(
        posthog_api_key,
        "SELECT properties.source_page AS source_page, properties.cta_id AS cta_id, "
        "properties.intent AS intent, count() AS total "
        "FROM events WHERE timestamp >= now() - INTERVAL 7 DAY "
        "AND event = 'affiliate_cta_click' "
        "GROUP BY source_page, cta_id, intent ORDER BY total DESC LIMIT 100",
    )
    try:
        referral_stats: dict[str, Any] = {
            "status": "available",
            **collect_referral_stats(
                referral_session,
                recent_start,
                recent_end,
                previous_start,
                previous_end,
            ),
        }
    except (ReferralAuthenticationError, ReferralRefreshError):
        # Referral authentication failures must not discard independent GSC/PostHog reads.
        # Never expose the exception text because it can contain session or credential data.
        referral_stats = {
            "status": "unavailable",
            "reason": "referral authentication or session refresh is unavailable",
        }

    return {
        "generated_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "gsc": {
            "site": GSC_SITE,
            "recent_range": [str(recent_start), str(recent_end)],
            "previous_range": [str(previous_start), str(previous_end)],
            "recent": aggregate(recent_daily),
            "previous": aggregate(previous_daily),
            "top_queries": top_queries[:25],
            "top_pages": top_pages[:25],
            "index_status": [inspect_url(credentials.token, url) for url in TARGET_URLS],
        },
        "posthog": {
            "range": "last_7_days",
            "events": posthog_events,
            "affiliate_breakdown": affiliate_breakdown,
        },
        "referral": {
            "agent_id": REFERRAL_AGENT_ID,
            "recent_range": [str(recent_start), str(recent_end)],
            "previous_range": [str(previous_start), str(previous_end)],
            **referral_stats,
        },
    }


def main() -> int:
    try:
        result = collect()
    except Exception:
        print("TAK12 collector failed; inspect protected runtime logs.", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
