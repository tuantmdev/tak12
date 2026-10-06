import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch

MONITORING_DIR = Path(__file__).resolve().parents[1]
if str(MONITORING_DIR) not in sys.path:
    sys.path.insert(0, str(MONITORING_DIR))

import tak12_monitor
import tak12_watchdog


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class ReferralQueryTests(unittest.TestCase):
    def test_http_401_raises_authentication_error(self):
        with patch.object(tak12_monitor.requests, "post", return_value=FakeResponse(401)):
            with self.assertRaises(tak12_monitor.ReferralAuthenticationError):
                tak12_monitor.referral_query("expired-cookie")

    def test_session_expired_payload_raises_authentication_error(self):
        response = FakeResponse(200, {"error": "session_expired", "message": "expired"})
        with patch.object(tak12_monitor.requests, "post", return_value=response):
            with self.assertRaises(tak12_monitor.ReferralAuthenticationError):
                tak12_monitor.referral_query("expired-cookie")

    def test_referral_query_rejects_redirect_without_forwarding_session(self):
        response = FakeResponse(302, headers={"Location": "https://example.invalid/collect"})
        with patch.object(tak12_monitor.requests, "post", return_value=response) as post:
            with self.assertRaisesRegex(RuntimeError, "redirect"):
                tak12_monitor.referral_query("sensitive-session")
        self.assertFalse(post.call_args.kwargs.get("allow_redirects", True))

    def test_session_persistence_failure_becomes_refresh_error(self):
        persist = getattr(
            tak12_monitor,
            "persist_refreshed_session",
            lambda _value: self.fail("persist_refreshed_session is missing"),
        )
        with patch.object(tak12_monitor, "store_secret_value", side_effect=PermissionError):
            with self.assertRaises(tak12_monitor.ReferralRefreshError):
                persist("sensitive-session")

    @patch("tak12_monitor.refresh_referral_session", return_value="fresh-cookie")
    @patch("tak12_monitor.referral_query")
    def test_expired_session_is_refreshed_once_for_all_windows(self, query, refresh):
        recent = {"clickCount": 3}
        previous = {"clickCount": 2}
        all_time = {"clickCount": 10}
        query.side_effect = [
            tak12_monitor.ReferralAuthenticationError("expired"),
            recent,
            previous,
            all_time,
        ]

        result = tak12_monitor.collect_referral_stats(
            "expired-cookie",
            date(2026, 7, 9),
            date(2026, 7, 15),
            date(2026, 7, 2),
            date(2026, 7, 8),
        )

        self.assertEqual(result, {"recent": recent, "previous": previous, "all_time": all_time})
        refresh.assert_called_once_with()
        self.assertEqual(query.call_count, 4)

    def test_store_secret_preserves_other_entries_and_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("OTHER=value\nTAK12_KC_SESSION=old\n")
            tak12_monitor.store_secret_value("TAK12_KC_SESSION", "new", env_file=env_file)
            self.assertEqual(env_file.read_text(), "OTHER=value\nTAK12_KC_SESSION=new\n")
            self.assertEqual(env_file.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(Path(temp_dir).glob(".env.tak12.*.tmp")), [])
            self.assertEqual((Path(temp_dir) / ".env.tak12.lock").stat().st_mode & 0o777, 0o600)

    def test_referral_session_prefers_refreshed_file_over_stale_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("TAK12_KC_SESSION=fresh\n")
            with patch.dict("os.environ", {"TAK12_KC_SESSION": "stale"}):
                value = tak12_monitor.secret_value(
                    "TAK12_KC_SESSION", prefer_file=True, env_file=env_file
                )
            self.assertEqual(value, "fresh")


class PartialReferralDataTests(unittest.TestCase):
    def common_patches(self, referral_error):
        return (
            patch.object(tak12_monitor, "gsc_credentials", return_value=type("Credentials", (), {"token": "token"})()),
            patch.object(tak12_monitor, "gsc_query", return_value=[]),
            patch.object(tak12_monitor, "inspect_url", return_value={"verdict": "PASS"}),
            patch.object(tak12_monitor, "secret_value", side_effect=lambda name, **_: "posthog-key" if name == "POSTHOG_API_KEY" else "secret-session"),
            patch.object(tak12_monitor, "posthog_query", return_value={"columns": [], "results": []}),
            patch.object(tak12_monitor, "collect_referral_stats", side_effect=referral_error),
        )

    def test_missing_playwright_preserves_gsc_and_posthog_without_secret_leak(self):
        secret = "never-log-this-session-value"
        patches = self.common_patches(tak12_monitor.ReferralRefreshError(f"Playwright missing: {secret}"))
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            result = tak12_monitor.collect()

        self.assertIn("gsc", result)
        self.assertIn("posthog", result)
        self.assertEqual(result["referral"]["status"], "unavailable")
        self.assertNotIn(secret, str(result))

    def test_missing_browser_preserves_partial_data(self):
        patches = self.common_patches(tak12_monitor.ReferralRefreshError("BrowserType.launch failed"))
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            result = tak12_monitor.collect()
        self.assertEqual(result["referral"]["status"], "unavailable")

    def test_unrelated_runtime_error_remains_fail_fast(self):
        patches = self.common_patches(RuntimeError("unexpected collector bug"))
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            with self.assertRaisesRegex(RuntimeError, "unexpected collector bug"):
                tak12_monitor.collect()

    def test_cli_failure_is_nonzero_and_does_not_print_server_message(self):
        secret = "server-echoed-session-secret"
        stderr = io.StringIO()
        with patch.object(tak12_monitor, "collect", side_effect=RuntimeError(secret)):
            with redirect_stderr(stderr):
                result = tak12_monitor.main()
        self.assertEqual(result, 1)
        self.assertIn("collector failed", stderr.getvalue())
        self.assertNotIn(secret, stderr.getvalue())


class WatchdogTests(unittest.TestCase):
    def test_unexpected_collector_failure_is_sanitized_and_nonzero_in_subprocess(self):
        secret = "server-echoed-session-secret"
        probe = f"""
import tak12_watchdog

def fail():
    raise ValueError({secret!r})

tak12_watchdog.collect = fail
raise SystemExit(tak12_watchdog.main())
"""
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=MONITORING_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
        rendered = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lỗi thu thập dữ liệu", rendered)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("Traceback", rendered)

    def test_malformed_collector_payload_is_sanitized_and_nonzero_in_subprocess(self):
        secret = "malformed-payload-secret"
        probe = f"""
import tak12_watchdog

tak12_watchdog.collect = lambda: {{
    "gsc": {{"recent": {{"clicks": 1, "impressions": 1}}, "previous": {{"clicks": 1, "impressions": 1}}, "index_status": []}},
    "posthog": {{"events": {{"results": []}}}},
    "referral": {{"status": "available", "recent": {{"unexpected": {secret!r}}}, "previous": {{}}}},
}}
raise SystemExit(tak12_watchdog.main())
"""
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=MONITORING_DIR,
            text=True,
            capture_output=True,
            check=False,
        )
        rendered = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lỗi thu thập dữ liệu", rendered)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("Traceback", rendered)

    @patch("tak12_watchdog.collect", side_effect=RuntimeError("secret-session-cookie"))
    def test_collection_failure_is_sanitized(self, _collect):
        output = io.StringIO()
        with redirect_stdout(output):
            tak12_watchdog.main()
        rendered = output.getvalue()
        self.assertIn("lỗi thu thập dữ liệu", rendered)
        self.assertNotIn("secret-session-cookie", rendered)

    @patch("tak12_watchdog.collect")
    def test_unavailable_referral_keeps_other_checks_and_one_alert(self, collect):
        secret = "never-print-this-session-value"
        collect.return_value = {
            "gsc": {
                "recent": {"clicks": 8, "impressions": 300},
                "previous": {"clicks": 20, "impressions": 600},
                "index_status": [],
            },
            "posthog": {"events": {"results": [["$pageview", 25]]}},
            "referral": {"status": "unavailable", "reason": secret},
        }
        output = io.StringIO()
        with redirect_stdout(output):
            tak12_watchdog.main()
        rendered = output.getvalue()
        self.assertIn("GSC impressions giảm", rendered)
        self.assertEqual(rendered.count("Referral"), 1)
        self.assertNotIn(secret, rendered)

    @patch("tak12_watchdog.collect")
    def test_available_referral_participates_in_grouped_traffic_alert(self, collect):
        collect.return_value = {
            "gsc": {
                "recent": {"clicks": 20, "impressions": 600},
                "previous": {"clicks": 20, "impressions": 600},
                "index_status": [],
            },
            "posthog": {"events": {"results": []}},
            "referral": {
                "status": "available",
                "recent": {"clickCount": 10},
                "previous": {"clickCount": 30},
            },
        }
        output = io.StringIO()
        with redirect_stdout(output):
            tak12_watchdog.main()
        rendered = output.getvalue()
        self.assertIn("referral clicks 30 → 10", rendered)
        self.assertNotIn("Referral unavailable", rendered)


class PackagingTests(unittest.TestCase):
    def test_wrapper_declares_dependencies_without_blocking_on_browser_install(self):
        wrapper = (MONITORING_DIR / "tak12_monitor.sh").read_text()
        self.assertIn("--with google-auth", wrapper)
        self.assertIn("--with requests", wrapper)
        self.assertIn("--with playwright", wrapper)
        self.assertNotIn("playwright install chromium", wrapper)
        self.assertNotIn("TAK12_PASSWORD", wrapper)

    def test_browser_provisioning_is_an_explicit_separate_step(self):
        provisioner = (MONITORING_DIR / "provision_browser.sh").read_text()
        self.assertIn("playwright install chromium", provisioner)


if __name__ == "__main__":
    unittest.main()
