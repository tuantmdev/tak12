"""Issue #18 contracts: calendar windows, aggregate completeness, fail-closed reports."""
import json
import sys
import unittest
from contextlib import ExitStack
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tak12_monitor as monitor


class CalendarTests(unittest.TestCase):
    def test_october_reproduces_manual_boundaries(self):
        windows = monitor.calendar_windows(date(2026, 10, 9))
        self.assertEqual(windows['recent']['start_utc'], '2026-10-03T07:00:00+00:00')
        self.assertEqual(windows['recent']['end_utc'], '2026-10-10T07:00:00+00:00')
        self.assertEqual(windows['previous']['start'], '2026-09-26')
        self.assertEqual(windows['previous']['end'], '2026-10-03')
        self.assertEqual(windows['recent']['timezone'], 'America/Los_Angeles')
        self.assertEqual(windows['recent']['bounds'], '[start, end)')

    def test_dst_and_equal_calendar_lengths_for_7_14_28_days(self):
        for end in (date(2026, 3, 10), date(2026, 11, 3)):
            for days in (7, 14, 28):
                windows = monitor.calendar_windows(end, days)
                hours = []
                for window in windows.values():
                    self.assertEqual((date.fromisoformat(window['end']) - date.fromisoformat(window['start'])).days, days)
                    hours.append((datetime.fromisoformat(window['end_utc']) - datetime.fromisoformat(window['start_utc'])).total_seconds() / 3600)
                self.assertEqual(windows['previous']['end'], windows['recent']['start'])
                self.assertEqual(abs(hours[0] - hours[1]), 1)


class AggregateTests(unittest.TestCase):
    def test_query_uses_exact_bounds_no_rolling_or_user_identifiers(self):
        window = monitor.calendar_windows(date(2026, 10, 9))['recent']
        query = monitor.baseline_query(window)
        self.assertIn("timestamp >= toDateTime('2026-10-03 07:00:00', 'UTC')", query)
        self.assertIn("timestamp < toDateTime('2026-10-10 07:00:00', 'UTC')", query)
        for key in ('source_page', 'cta_id', 'position', 'intent', 'destination_url'):
            self.assertIn('missing_' + key, query)
        self.assertIn('properties.$pathname', query)
        self.assertIn('path(properties.$current_url)', query)
        self.assertIn('2026-07-16 17:21:00', query)
        self.assertIn("'cta_click'", query)
        self.assertNotIn('now()', query)
        self.assertNotIn('distinct_id', query)
        self.assertNotIn('LIMIT 100', query)
        self.assertNotIn('properties.destination_url AS', query)

    def payload(self):
        return {'columns': monitor.BASELINE_COLUMNS, 'results': [
            ['/', '$pageview', 'post_cutover', None, None, 10, 10, 0, 0, 0, 0],
            ['/', 'affiliate_cta_click', 'post_cutover', 'final_cta', 'free_account', 2, 0, 0, 1, 0, 1],
            ['/', 'cta_click', 'pre_cutover', None, None, 3, 3, 3, 3, 3, 3],
            [None, 'affiliate_cta_click', 'post_cutover', None, None, 1, 1, 1, 1, 1, 1],
        ]}

    def test_denominators_missing_fields_and_legacy_remain_separate(self):
        result = monitor.summarize_baseline(self.payload())
        self.assertEqual(result['status'], 'available')
        home = next(page for page in result['pages'] if page['source_page'] == '/')
        self.assertEqual(home['pageviews'], 10)
        self.assertEqual(home['affiliate_cta_click'], 2)
        self.assertEqual(home['cta_click'], 3)
        self.assertEqual(home['cta_breakdown'][0]['cta_id'], 'final_cta')
        self.assertEqual(result['missing']['affiliate_cta_click']['destination_url'], 2)
        self.assertEqual(result['missing']['$pageview']['source_page'], 10)
        self.assertEqual(result['unmapped_source_page_events'], 1)
        self.assertEqual(result['organic_attribution']['status'], 'unverified')
        self.assertIsNone(result['organic_attribution']['counts'])
        self.assertEqual(len(home['schema_periods']), 2)

    def test_missing_result_or_truncation_is_not_a_zero_baseline(self):
        for payload in ({}, {'columns': [], 'results': []}, {**self.payload(), 'hasMore': True}, {**self.payload(), 'is_cached': True, 'error': 'private server detail'}):
            result = monitor.summarize_baseline(payload)
            self.assertEqual(result['status'], 'unavailable')
            self.assertIsNone(result['pages'])
            self.assertNotIn('private server detail', json.dumps(result))

    def test_valid_empty_result_is_zero_but_not_organic(self):
        result = monitor.summarize_baseline({'columns': monitor.BASELINE_COLUMNS, 'results': []})
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['pages'], [])
        self.assertIsNone(result['organic_attribution']['counts'])

    def test_arbitrary_dimension_values_never_escape_in_report(self):
        payload = self.payload()
        payload['results'][1][:5] = ['/private@example.com?token=private', 'affiliate_cta_click', 'post_cutover', 'private@example.com', 'private@example.com']
        result = monitor.summarize_baseline(payload)
        self.assertNotIn('private', json.dumps(result))

    def test_malformed_counts_fail_closed(self):
        for bad in (-1, '2', None):
            payload = self.payload()
            payload['results'][0][5] = bad
            self.assertEqual(monitor.summarize_baseline(payload)['status'], 'unavailable')

    def test_posthog_transport_preserves_incomplete_signal(self):
        response = type('Response', (), {'raise_for_status': lambda self: None, 'json': lambda self: {'columns': monitor.BASELINE_COLUMNS, 'results': [], 'hasMore': True}})()
        with patch.object(monitor.requests, 'post', return_value=response):
            result = monitor.posthog_query('test-key', 'SELECT count() FROM events')
        self.assertTrue(result['hasMore'])

    def test_transport_handles_null_status_and_sanitizes_non_object_payload(self):
        for payload, available in (({'columns': monitor.BASELINE_COLUMNS, 'results': [], 'query_status': None}, True), (None, False), ([], False), ({'columns': monitor.BASELINE_COLUMNS, 'results': [], 'query_status': {'complete': False}}, False)):
            response = type('Response', (), {'raise_for_status': lambda self: None, 'json': lambda self: payload})()
            with patch.object(monitor.requests, 'post', return_value=response):
                result = monitor.summarize_baseline(monitor.posthog_query('test-key', 'SELECT count() FROM events'))
            self.assertEqual(result['status'], 'available' if available else 'unavailable')

    def test_async_errors_cannot_be_accepted_as_empty_success(self):
        for status in ({'complete': True, 'error': True}, {'complete': True, 'error_message': 'private'}, {'error': True}, {}):
            payload = {'columns': monitor.BASELINE_COLUMNS, 'results': [], 'query_status': status}
            response = type('Response', (), {'raise_for_status': lambda self: None, 'json': lambda self: payload})()
            with patch.object(monitor.requests, 'post', return_value=response):
                result = monitor.summarize_baseline(monitor.posthog_query('test-key', 'SELECT count() FROM events'))
            self.assertEqual(result['status'], 'unavailable')
            self.assertNotIn('private', json.dumps(result))

    def test_unknown_dimensions_are_counted_without_assuming_complete_intent(self):
        payload = self.payload()
        payload['results'][1][3:5] = [None, None]
        result = monitor.summarize_baseline(payload)
        self.assertEqual(result['unmapped_dimensions']['affiliate_cta_click']['cta_id'], 3)
        self.assertEqual(result['unmapped_dimensions']['affiliate_cta_click']['intent'], 3)

    def test_truncated_or_malformed_rows_and_counts_fail_closed(self):
        cases = [None, [], {'columns': monitor.BASELINE_COLUMNS, 'results': [[{}]]}]
        payload = self.payload()
        payload['results'][0][6] = 11
        cases.append(payload)
        cases.append({'columns': monitor.BASELINE_COLUMNS, 'results': self.payload()['results'][:1] * monitor.AGGREGATE_ROW_LIMIT})
        for payload in cases:
            self.assertEqual(monitor.summarize_baseline(payload)['status'], 'unavailable')

    def test_partial_rolling_data_cannot_trigger_false_watchdog_alert(self):
        for payload in (
            {'columns': ['event', 'total'], 'results': [['$pageview', 47]], 'incomplete': True},
            {'columns': ['event', 'total'], 'results': [['$pageview', 47]], 'hasMore': True},
            {'columns': ['event', 'total'], 'results': [['private@example.com', 47]]},
            {'columns': ['event', 'total'], 'results': [['$pageview', -1]]},
            {},
        ):
            result = monitor.summarize_instrumentation(payload)
            self.assertEqual(result['status'], 'unavailable')
            self.assertEqual(result['results'], [])
            self.assertNotIn('private', json.dumps(result))

    def test_complete_rolling_data_preserves_watchdog_counts(self):
        rows = [['$pageview', 47], ['affiliate_cta_click', 5], ['cta_click', 3]]
        result = monitor.summarize_instrumentation({'columns': ['event', 'total'], 'results': rows})
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['results'], rows)


class CollectionTests(unittest.TestCase):
    def collect(self, referral_error=None, daily=None):
        with ExitStack() as stack:
            stack.enter_context(patch.object(monitor, 'gsc_credentials', return_value=type('Credentials', (), {'token': 'test-token'})()))
            gsc = stack.enter_context(patch.object(monitor, 'gsc_query', return_value=daily or []))
            stack.enter_context(patch.object(monitor, 'inspect_url', return_value={}))
            stack.enter_context(patch.object(monitor, 'secret_value', return_value='test-secret'))
            posthog = stack.enter_context(patch.object(monitor, 'posthog_query', return_value={'columns': [], 'results': []}))
            stack.enter_context(patch.object(monitor, 'collect_referral_stats', side_effect=referral_error, return_value={'recent': {'clickCount': 44, 'signupCount': 2}, 'previous': {}, 'all_time': {}}))
            result = monitor.collect(final_end=date(2026, 10, 9), collected_at=datetime(2026, 10, 12, 2, tzinfo=timezone.utc))
        return result, gsc, posthog

    def test_every_source_declares_metadata_and_rates_are_disabled(self):
        result, gsc, posthog = self.collect(daily=[{'keys': ['2026-10-09'], 'clicks': 18}])
        for source in ('gsc', 'posthog', 'referral'):
            for name in ('recent', 'previous'):
                window = result[source]['windows'][name]
                for key in ('start', 'end', 'bounds', 'timezone', 'scope', 'final_data_through'):
                    self.assertIn(key, window)
        self.assertEqual(result['gsc']['windows']['recent']['final_data_through'], '2026-10-09')
        self.assertIsNone(result['posthog']['windows']['recent']['final_data_through'])
        self.assertIsNone(result['referral']['windows']['recent']['timezone'])
        self.assertIsNone(result['referral']['site_only_attribution'])
        self.assertEqual(result['referral']['windows']['recent']['bounds'], 'unknown')
        self.assertFalse(result['comparability']['cross_source_rates_enabled'])
        self.assertIsNone(result['comparability']['rates'])
        self.assertEqual(set(result['gsc']['comparisons']), {'7', '14', '28'})
        self.assertEqual(result['posthog']['stable']['recent']['status'], 'unavailable')
        self.assertEqual(result['posthog']['instrumentation']['window']['end'], '2026-10-12T02:00:00+00:00')
        self.assertEqual(result['posthog']['instrumentation']['window']['start'], '2026-10-05T02:00:00+00:00')
        self.assertTrue(any('2026-10-03 07:00:00' in call.args[1] for call in posthog.call_args_list))
        ranges = {(call.args[1], call.args[2]) for call in gsc.call_args_list}
        self.assertIn((date(2026, 9, 12), date(2026, 10, 9)), ranges)
        self.assertIn((date(2026, 8, 15), date(2026, 9, 11)), ranges)

    def test_empty_gsc_and_partial_referral_never_claim_finality_or_comparability(self):
        result, _, _ = self.collect(monitor.ReferralRefreshError('private-cookie'))
        self.assertIsNone(result['gsc']['windows']['recent']['final_data_through'])
        self.assertEqual(result['referral']['status'], 'unavailable')
        self.assertIn('windows', result['referral'])
        self.assertFalse(result['comparability']['cross_source_rates_enabled'])
        self.assertNotIn('private-cookie', json.dumps(result))

    def test_referral_available_does_not_imply_comparability(self):
        result, _, _ = self.collect()
        self.assertEqual(result['referral']['status'], 'available')
        self.assertFalse(result['comparability']['cross_source_rates_enabled'])
        self.assertIsNone(result['comparability']['rates'])


if __name__ == '__main__':
    unittest.main()
