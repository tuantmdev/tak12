import io
import json
import sys
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tak12_monitor as monitor


class PostHogFailureTests(unittest.TestCase):
    def test_one_failed_query_preserves_independent_results_without_secrets(self):
        secret = 'private-api-key-and-server-response'
        failures = (
            ('post', monitor.requests.Timeout(secret)),
            ('post', monitor.requests.ConnectionError(secret)),
            ('raise_for_status', monitor.requests.HTTPError(secret)),
            ('json', monitor.requests.exceptions.JSONDecodeError(secret, secret, 0)),
            ('json', json.JSONDecodeError(secret, secret, 0)),
        )
        # Query order: stable recent/previous, rolling events, rolling baseline,
        # hostname parser probe, site-scope recent/previous.
        probe = {'columns': [label for label, _url, _bucket in monitor.HOST_PARSER_CASES],
                 'results': [[bucket for _label, _url, bucket in monitor.HOST_PARSER_CASES]]}
        for stage, error in failures:
            for failed_index in range(7):
                with self.subTest(stage=stage, error=type(error).__name__, query=failed_index):
                    responses = []
                    for index in range(7):
                        payload = (
                            {'columns': ['event', 'total'], 'results': [['$pageview', 47]]}
                            if index == 2 else probe if index == 4 else
                            {'columns': monitor.SITE_SCOPE_COLUMNS, 'results': []} if index > 4 else
                            {'columns': monitor.BASELINE_COLUMNS, 'results': []}
                        )
                        response = Mock()
                        response.json.return_value = payload
                        if index == failed_index:
                            if stage == 'post':
                                response = error
                            else:
                                getattr(response, stage).side_effect = error
                        responses.append(response)
                    output = io.StringIO()
                    with ExitStack() as stack:
                        stack.enter_context(redirect_stdout(output))
                        stack.enter_context(redirect_stderr(output))
                        stack.enter_context(patch.object(monitor, 'gsc_credentials', return_value=Mock(token='test-token')))
                        stack.enter_context(patch.object(monitor, 'gsc_query', return_value=[{'keys': ['2026-10-09'], 'clicks': 18}]))
                        stack.enter_context(patch.object(monitor, 'inspect_url', return_value={'verdict': 'PASS'}))
                        stack.enter_context(patch.object(monitor, 'secret_value', return_value=secret))
                        stack.enter_context(patch.object(monitor, 'collect_referral_stats', return_value={'recent': {'clickCount': 44}, 'previous': {'clickCount': 22}, 'all_time': {'clickCount': 99}}))
                        post = stack.enter_context(patch.object(monitor.requests, 'post', side_effect=responses))
                        result = monitor.collect(final_end=date(2026, 10, 9), collected_at=datetime(2026, 10, 12, tzinfo=timezone.utc))
                    # A failed parser probe fails closed: no site-scope queries are sent.
                    self.assertEqual(post.call_count, 5 if failed_index == 4 else 7)
                    scope = result['posthog']['site_scope']
                    summaries = [result['posthog']['stable']['recent'], result['posthog']['stable']['previous'], result['posthog']['events'], result['posthog']['instrumentation']['baseline']]
                    for index, summary in enumerate(summaries):
                        self.assertEqual(summary['status'], 'unavailable' if index == failed_index else 'available')
                    self.assertEqual(scope['parser']['status'], 'unavailable' if failed_index == 4 else 'verified')
                    for index, name in ((5, 'recent'), (6, 'previous')):
                        self.assertEqual(scope[name]['status'], 'unavailable' if failed_index in (4, index) else 'available')
                        self.assertIsNone(scope[name]['organic']['counts'])
                    self.assertFalse(result['comparability']['cross_source_rates_enabled'])
                    if failed_index != 2:
                        self.assertEqual(result['posthog']['events']['results'], [['$pageview', 47]])
                    else:
                        self.assertEqual(result['posthog']['events']['results'], [])
                    self.assertEqual(result['gsc']['recent']['clicks'], 18)
                    self.assertEqual(set(result['gsc']['comparisons']), {'7', '14', '28'})
                    self.assertEqual(result['referral']['status'], 'available')
                    self.assertEqual(result['referral']['recent']['clickCount'], 44)
                    self.assertEqual(result['referral']['previous']['clickCount'], 22)
                    self.assertEqual(result['referral']['all_time']['clickCount'], 99)
                    self.assertNotIn(secret, json.dumps(result) + output.getvalue())

    def test_unexpected_errors_remain_fail_fast(self):
        for stage in ('post', 'raise_for_status', 'json'):
            for error in (RuntimeError('unexpected bug'), ValueError('unexpected value')):
                with self.subTest(stage=stage, error=type(error).__name__):
                    response = Mock()
                    if stage != 'post':
                        getattr(response, stage).side_effect = error
                    with patch.object(monitor.requests, 'post', return_value=response, side_effect=error if stage == 'post' else None):
                        with self.assertRaises(type(error)):
                            monitor.posthog_query('test-key', 'SELECT 1')
