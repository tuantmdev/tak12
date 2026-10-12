#!/usr/bin/env python3
"""Read-only TAK12 growth monitor for GSC, PostHog, and referral results."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import fcntl
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
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
    try:
        response = requests.post(
            f"{POSTHOG_HOST}/api/projects/{POSTHOG_PROJECT_ID}/query/",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"query": {"kind": "HogQLQuery", "query": hogql}},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.HTTPError, requests.Timeout, requests.ConnectionError,
            requests.exceptions.JSONDecodeError, json.JSONDecodeError):
        return {"incomplete": True}
    if not isinstance(payload, dict):
        return {"incomplete": True}
    query_status = payload.get("query_status")
    incomplete = query_status is not None and (
        not isinstance(query_status, dict) or query_status.get("complete") is not True
        or bool(query_status.get("error") or query_status.get("error_message"))
    )
    return {
        "columns": payload.get("columns"), "results": payload.get("results"),
        "hasMore": payload.get("hasMore", False),
        "incomplete": bool(payload.get("error") or incomplete),
    }


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


GSC_TIMEZONE = "America/Los_Angeles"
TRACKING_CUTOVER = "2026-07-16 17:21:00"
AGGREGATE_ROW_LIMIT = 50000
REPORT_DIMENSIONS = json.loads(Path(__file__).with_name("report_dimensions.json").read_text())
MISSING_FIELDS = ("source_page", "cta_id", "position", "intent", "destination_url")
BASELINE_COLUMNS = ["source_page", "event", "schema_period", "cta_id", "intent", "total"] + [
    "missing_" + field for field in MISSING_FIELDS
]
POSTHOG_SCOPE = "project 504827; all traffic; site-only and organic attribution unverified; event counts, not users/sessions"
GSC_SCOPE = "sc-domain:tak-12.com; Google organic web search; clicks/impressions"
REFERRAL_SCOPE = "agent 210; acquisition surfaces unknown; site-only attribution unverified"


def calendar_windows(final_end: date, days: int = 7) -> dict[str, dict[str, Any]]:
    """Equal calendar-day windows, even when their UTC durations differ across DST."""
    if days <= 0:
        raise ValueError("Window length must be positive")
    zone = ZoneInfo(GSC_TIMEZONE)
    end = final_end + timedelta(days=1)
    windows = {}
    for name, offset in (("recent", 0), ("previous", days)):
        stop = end - timedelta(days=offset)
        start = stop - timedelta(days=days)
        windows[name] = {
            "start": str(start), "end": str(stop), "bounds": "[start, end)",
            "timezone": GSC_TIMEZONE, "calendar_days": days,
            "start_utc": datetime.combine(start, time.min, zone).astimezone(timezone.utc).isoformat(),
            "end_utc": datetime.combine(stop, time.min, zone).astimezone(timezone.utc).isoformat(),
        }
    return windows


def timestamp_filter(window: dict[str, Any]) -> str:
    def sql_timestamp(value: str) -> str:
        return datetime.fromisoformat(value).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"timestamp >= toDateTime('{sql_timestamp(window['start_utc'])}', 'UTC') "
        f"AND timestamp < toDateTime('{sql_timestamp(window['end_utc'])}', 'UTC')"
    )


def baseline_query(window: dict[str, Any]) -> str:
    """Only aggregate counts and public, allowlisted dimensions leave PostHog."""
    def allowlisted(expression: str, field: str) -> str:
        # This versioned catalogue contains public site labels, never event-derived values.
        literals = ", ".join("'" + value.replace("'", "''") + "'" for value in REPORT_DIMENSIONS[field])
        return f"if({expression} IN ({literals}), {expression}, NULL)"

    page = "coalesce(nullIf(properties.source_page, ''), nullIf(properties.$pathname, ''), path(properties.$current_url))"
    columns = [
        allowlisted(page, "source_page") + " AS source_page",
        "event",
        f"if(timestamp < toDateTime('{TRACKING_CUTOVER}', 'UTC'), 'pre_cutover', 'post_cutover') AS schema_period",
        "if(event = '$pageview', NULL, " + allowlisted("properties.cta_id", "cta_id") + ") AS cta_id",
        "if(event = '$pageview', NULL, " + allowlisted("properties.intent", "intent") + ") AS intent",
        "count() AS total",
    ]
    for field in MISSING_FIELDS:
        applicable = "" if field == "source_page" else "event != '$pageview' AND "
        columns.append(
            f"countIf({applicable}trim(ifNull(toString(properties.{field}), '')) = '') AS missing_{field}"
        )
    return (
        "SELECT " + ", ".join(columns) + " FROM events WHERE " + timestamp_filter(window)
        + " AND event IN ('$pageview', 'cta_click', 'affiliate_cta_click') "
        + "GROUP BY source_page, event, schema_period, cta_id, intent "
        + "ORDER BY source_page, event, schema_period, cta_id, intent "
        + f"LIMIT {AGGREGATE_ROW_LIMIT}"
    )


def summarize_baseline(payload: dict[str, Any]) -> dict[str, Any]:
    """Reject incomplete aggregates; do not turn a missing response into zero traffic."""
    organic = {"status": "unverified", "counts": None, "reason": "No verified event-level organic attribution contract"}
    unavailable = {
        "status": "unavailable", "pages": None,
        "reason": "Missing, malformed or potentially truncated aggregate response",
        "organic_attribution": organic,
    }
    if not isinstance(payload, dict):
        return unavailable
    rows = payload.get("results")
    if (payload.get("columns") != BASELINE_COLUMNS or not isinstance(rows, list)
            or payload.get("hasMore") or payload.get("error") or payload.get("incomplete")
            or len(rows) >= AGGREGATE_ROW_LIMIT):
        return unavailable
    events = ("$pageview", "affiliate_cta_click", "cta_click")
    missing = {event: dict.fromkeys(MISSING_FIELDS, 0) for event in events}
    unmapped_dimensions = {event: {field: 0 for field in REPORT_DIMENSIONS} for event in events}
    pages: dict[str | None, dict[str, Any]] = {}
    unmapped = 0
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != len(BASELINE_COLUMNS):
            return unavailable
        source, event, period, cta, intent, total, *counts = row
        if (event not in events or period not in ("pre_cutover", "post_cutover")
                or any(type(value) is not int or value < 0 for value in [total, *counts])
                or any(value > total for value in counts)):
            return unavailable
        source = source if source in REPORT_DIMENSIONS["source_page"] else None
        cta = cta if cta in REPORT_DIMENSIONS["cta_id"] else None
        intent = intent if intent in REPORT_DIMENSIONS["intent"] else None
        for field, value in (("source_page", source), ("cta_id", cta), ("intent", intent)):
            if value is None and (field == "source_page" or event != "$pageview"):
                unmapped_dimensions[event][field] += total
        if source is None:
            unmapped += total
        page = pages.setdefault(source, {
            "source_page": source, "pageviews": 0, "affiliate_cta_click": 0,
            "cta_click": 0, "cta_breakdown": [], "schema_periods": {},
        })
        metric = "pageviews" if event == "$pageview" else event
        page[metric] += total
        period_counts = page["schema_periods"].setdefault(period, {"pageviews": 0, "affiliate_cta_click": 0, "cta_click": 0})
        period_counts[metric] += total
        if event != "$pageview":
            page["cta_breakdown"].append({"event": event, "schema_period": period, "cta_id": cta, "intent": intent, "total": total})
        for field, count in zip(MISSING_FIELDS, counts):
            missing[event][field] += count
    return {
        "status": "available", "pages": list(pages.values()), "missing": missing,
        "unmapped_source_page_events": unmapped, "unmapped_dimensions": unmapped_dimensions,
        "organic_attribution": organic,
        "counts_unit": "events, not users/sessions; pageview fallback does not imply source_page completeness",
    }


def summarize_instrumentation(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep partial rolling counts out of the legacy watchdog compatibility alias."""
    unavailable = {
        "status": "unavailable", "columns": ["event", "total"], "results": [],
        "reason": "Missing, malformed or incomplete instrumentation; empty results are not zero traffic",
    }
    if (not isinstance(payload, dict) or payload.get("columns") != ["event", "total"]
            or not isinstance(payload.get("results"), list) or payload.get("incomplete")
            or payload.get("hasMore") or payload.get("error")):
        return unavailable
    seen = set()
    for row in payload["results"]:
        if (not isinstance(row, (list, tuple)) or len(row) != 2
                or row[0] not in ("$pageview", "affiliate_cta_click", "cta_click", "quiz_started", "quiz_completed")
                or row[0] in seen or type(row[1]) is not int or row[1] < 0):
            return unavailable
        seen.add(row[0])
    return {"status": "available", "columns": ["event", "total"], "results": payload["results"]}


def collect(*, final_end: date | None = None, collected_at: datetime | None = None) -> dict[str, Any]:
    collected_at = collected_at or datetime.now(timezone.utc)
    if collected_at.tzinfo is None:
        raise ValueError("Collection timestamp must include a timezone")
    collected_at = collected_at.astimezone(timezone.utc).replace(microsecond=0)
    # Retain the existing three-day lag, explicitly anchored to the UTC run date.
    final_end = final_end or collected_at.date() - timedelta(days=3)
    credentials = gsc_credentials()
    comparisons = {}
    for days in (7, 14, 28):
        windows = calendar_windows(final_end, days)
        comparison = {"windows": windows}
        for name, window in windows.items():
            start = date.fromisoformat(window["start"])
            end = date.fromisoformat(window["end"]) - timedelta(days=1)
            rows = gsc_query(credentials.token, start, end, ["date"], 100)
            returned_dates = [row["keys"][0] for row in rows if row.get("keys") and str(start) <= row["keys"][0] <= str(end)]
            window.update({
                "scope": GSC_SCOPE, "final_data_through": max(returned_dates, default=None),
                "finality_basis": "latest returned date with final data; missing dates may have no traffic",
                "requested_final_end": str(end), "api_bounds": "startDate/endDate inclusive",
            })
            comparison[name] = aggregate(rows)
        comparisons[str(days)] = comparison
    weekly = comparisons["7"]
    gsc_windows = weekly["windows"]
    recent_start = date.fromisoformat(gsc_windows["recent"]["start"])
    recent_end = final_end
    previous_start = date.fromisoformat(gsc_windows["previous"]["start"])
    previous_end = recent_start - timedelta(days=1)
    top_queries = gsc_query(credentials.token, recent_start, recent_end, ["query"], 50)
    top_pages = gsc_query(credentials.token, recent_start, recent_end, ["page"], 50)

    posthog_api_key = secret_value("POSTHOG_API_KEY")
    if not posthog_api_key:
        raise RuntimeError("POSTHOG_API_KEY is not available")
    referral_session = secret_value("TAK12_KC_SESSION", prefer_file=True)
    posthog_windows = {
        name: {**window, "scope": POSTHOG_SCOPE, "final_data_through": None,
               "finality_basis": "event store; late arrivals possible"}
        for name, window in calendar_windows(final_end).items()
    }
    stable = {
        name: summarize_baseline(posthog_query(posthog_api_key, baseline_query(window)))
        for name, window in posthog_windows.items()
    }
    rolling_start = (collected_at - timedelta(days=7)).isoformat()
    rolling_end = collected_at.isoformat()
    rolling_window = {
        "start": rolling_start, "end": rolling_end, "start_utc": rolling_start, "end_utc": rolling_end,
        "bounds": "[start, end)", "timezone": "UTC", "scope": POSTHOG_SCOPE,
        "final_data_through": None,
    }
    posthog_events = summarize_instrumentation(posthog_query(
        posthog_api_key,
        "SELECT event, count() AS total FROM events WHERE " + timestamp_filter(rolling_window)
        + " AND event IN ('$pageview', 'cta_click', 'affiliate_cta_click', 'quiz_started', 'quiz_completed') "
        + "GROUP BY event ORDER BY total DESC",
    ))
    rolling_baseline = summarize_baseline(posthog_query(posthog_api_key, baseline_query(rolling_window)))
    affiliate_rows = [
        [page["source_page"], cta["cta_id"], cta["intent"], cta["total"], cta["schema_period"]]
        for page in (rolling_baseline["pages"] or []) for cta in page["cta_breakdown"]
        if cta["event"] == "affiliate_cta_click"
    ]
    try:
        referral_stats: dict[str, Any] = {
            "status": "available",
            **collect_referral_stats(referral_session, recent_start, recent_end, previous_start, previous_end),
        }
    except (ReferralAuthenticationError, ReferralRefreshError):
        referral_stats = {
            "status": "unavailable",
            "reason": "referral authentication or session refresh is unavailable",
        }
    referral_windows = {
        name: {"start": str(start), "end": str(end), "bounds": "unknown", "timezone": None,
               "scope": REFERRAL_SCOPE, "final_data_through": None,
               "date_parameters": "requested fromDate/toDate; endpoint semantics unverified"}
        for name, start, end in (("recent", recent_start, recent_end), ("previous", previous_start, previous_end))
    }
    referral_windows["all_time"] = {
        "start": None, "end": None, "bounds": "unknown", "timezone": None,
        "scope": REFERRAL_SCOPE, "final_data_through": None,
    }
    return {
        "generated_at_utc": collected_at.isoformat(),
        "gsc": {
            "site": GSC_SITE, "windows": gsc_windows, "comparisons": comparisons,
            "recent_range": [str(recent_start), str(recent_end)],
            "previous_range": [str(previous_start), str(previous_end)],
            "recent": weekly["recent"], "previous": weekly["previous"],
            "top_queries": top_queries[:25], "top_pages": top_pages[:25],
            "index_status": [inspect_url(credentials.token, url) for url in TARGET_URLS],
        },
        "posthog": {
            "windows": posthog_windows, "stable": stable,
            "instrumentation": {"label": "rolling 7-day instrumentation; not the stable baseline",
                                "window": rolling_window, "baseline": rolling_baseline,
                                "tracking_cutover_utc": TRACKING_CUTOVER + "Z"},
            # Compatibility aliases used by the existing watchdog: explicitly rolling.
            "range": "last_7_days", "events": posthog_events,
            "affiliate_breakdown": {"status": rolling_baseline["status"],
                                    "columns": ["source_page", "cta_id", "intent", "total", "schema_period"],
                                    "results": affiliate_rows if rolling_baseline["status"] == "available" else None},
        },
        "referral": {
            "agent_id": REFERRAL_AGENT_ID, "windows": referral_windows,
            "site_only_attribution": None, "verification": "No authoritative timezone or site-only scope contract supplied",
            "recent_range": [str(recent_start), str(recent_end)],
            "previous_range": [str(previous_start), str(previous_end)],
            **referral_stats,
        },
        "comparability": {
            "cross_source_rates_enabled": False, "rates": None,
            "reasons": ["GSC search clicks and PostHog all-traffic events are different populations/units",
                        "PostHog organic attribution and site-only scope are unverified",
                        "Referral timezone, boundary semantics and acquisition surfaces are unknown"],
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
