"""Issue #20 contracts: CTA ID presence/recognition categories, never raw values."""
import json
import sys
import unittest
from contextlib import ExitStack
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tak12_monitor as monitor
import test_site_scope as site_fixtures


def rolling_window():
    start, end = '2026-10-19T02:00:18+00:00', '2026-10-26T02:00:18+00:00'
    return {'start': start, 'end': end, 'start_utc': start, 'end_utc': end}


class QueryTests(unittest.TestCase):
    def test_query_buckets_into_fixed_categories_without_raw_values(self):
        query = monitor.cta_id_category_query(rolling_window())
        self.assertEqual(monitor.CTA_ID_CATEGORIES, ('absent', 'empty', 'recognized', 'nonempty_unrecognized'))
        self.assertIn("timestamp >= toDateTime('2026-10-19 02:00:18', 'UTC')", query)
        self.assertIn("timestamp < toDateTime('2026-10-26 02:00:18', 'UTC')", query)
        self.assertIn("event IN ('affiliate_cta_click', 'cta_click')", query)
        self.assertIn('properties.cta_id IS NULL', query)
        self.assertIn("'^[[:space:]]*$'", query)
        self.assertIn("'quiz_result'", query)
        for category in monitor.CTA_ID_CATEGORIES:
            self.assertIn(f"'{category}'", query)
        self.assertIn('GROUP BY event, schema_period, cta_id_category', query)
        self.assertIn(f'LIMIT {monitor.AGGREGATE_ROW_LIMIT}', query)
        for forbidden in ('properties.cta_id AS', 'distinct_id', 'person', 'now()', 'uniq', 'groupArray',
                          'any(', 'LIKE', 'lower('):
            self.assertNotIn(forbidden, query)


def payload(rows=None):
    return {'columns': monitor.CTA_ID_COLUMNS, 'results': rows if rows is not None else [
        ['affiliate_cta_click', 'post_cutover', 'recognized', 4, 0],
        ['affiliate_cta_click', 'post_cutover', 'nonempty_unrecognized', 1, 0],
        ['cta_click', 'post_cutover', 'absent', 2, 0],
        ['cta_click', 'post_cutover', 'empty', 3, 0],
        ['cta_click', 'pre_cutover', 'recognized', 5, 0],
    ]}


class SummaryTests(unittest.TestCase):
    def test_counts_each_category_by_event_and_schema_period(self):
        result = monitor.summarize_cta_id_categories(payload())
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['totals'], {'absent': 2, 'empty': 3, 'recognized': 9, 'nonempty_unrecognized': 1})
        self.assertEqual(result['total'], 15)
        self.assertEqual(result['by_event']['affiliate_cta_click'],
                         {'absent': 0, 'empty': 0, 'recognized': 4, 'nonempty_unrecognized': 1})
        self.assertEqual(result['by_event']['cta_click'],
                         {'absent': 2, 'empty': 3, 'recognized': 5, 'nonempty_unrecognized': 0})
        self.assertEqual(result['schema_periods']['pre_cutover']['recognized'], 5)
        self.assertEqual(result['schema_periods']['post_cutover']['recognized'], 4)
        self.assertEqual(result['counts_unit'], 'events, not users/sessions')

    def test_quiz_result_is_a_recognized_catalogue_id_and_counted(self):
        self.assertIn('quiz_result', monitor.REPORT_DIMENSIONS['cta_id'])
        result = monitor.summarize_cta_id_categories(payload([
            ['cta_click', 'post_cutover', 'recognized', 5, 2],
            ['affiliate_cta_click', 'post_cutover', 'recognized', 3, 1],
        ]))
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['totals']['recognized'], 8)
        self.assertEqual(result['quiz_result'], {'category': 'recognized', 'total': 3,
                                                 'by_event': {'affiliate_cta_click': 1, 'cta_click': 2}})
        self.assertEqual(monitor.summarize_cta_id_categories(payload())['quiz_result']['total'], 0)

    def test_unknown_ids_stay_explicit_and_are_never_labeled_missing(self):
        result = monitor.summarize_cta_id_categories(payload())
        self.assertEqual(result['unknown'], {'category': 'nonempty_unrecognized', 'total': 1, 'mapping': None})
        self.assertEqual(result['missing'], {'categories': ['absent', 'empty'], 'total': 5})
        self.assertNotIn('nonempty_unrecognized', result['missing']['categories'])
        self.assertIn('not missing', result['semantics']['nonempty_unrecognized'])
        self.assertIn('whitespace', result['semantics']['empty'])
        self.assertIn('exact', result['semantics']['recognized'])

    def test_valid_empty_window_is_zero_not_unavailable(self):
        result = monitor.summarize_cta_id_categories(payload([]))
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['totals'], dict.fromkeys(monitor.CTA_ID_CATEGORIES, 0))
        self.assertEqual(result['quiz_result']['total'], 0)

    def assert_unavailable(self, result):
        self.assertEqual(result['status'], 'unavailable')
        for key in ('totals', 'total', 'by_event', 'schema_periods', 'quiz_result', 'unknown', 'missing'):
            self.assertIsNone(result[key], key)
        text = json.dumps(result)
        self.assertNotIn('private', text)
        self.assertNotIn('evil', text)

    def test_missing_incomplete_or_malformed_payload_fails_closed(self):
        cases = [None, [], {}, {'columns': [], 'results': []},
                 {'columns': monitor.CTA_ID_COLUMNS[:-1], 'results': []},
                 {'columns': monitor.CTA_ID_COLUMNS, 'results': None},
                 {**payload(), 'incomplete': True},
                 {**payload(), 'error': 'private server detail'}]
        for case in cases:
            with self.subTest(case=case):
                self.assert_unavailable(monitor.summarize_cta_id_categories(case))

    def test_truncated_results_fail_closed(self):
        row = payload()['results'][0]
        for case in ({**payload(), 'hasMore': True},
                     payload([list(row) for _ in range(monitor.AGGREGATE_ROW_LIMIT)])):
            self.assert_unavailable(monitor.summarize_cta_id_categories(case))

    def test_malformed_rows_or_unexpected_labels_fail_closed_without_echoing_values(self):
        bad_rows = [
            None, 'private', {}, [],
            ['cta_click', 'post_cutover', 'recognized', 1],
            ['cta_click', 'post_cutover', 'recognized', 1, 0, 0],
            ['cta_click', 'post_cutover', 'private_raw_cta_value', 1, 0],
            ['cta_click', 'post_cutover', 'missing', 1, 0],
            ['cta_click', 'post_cutover', None, 1, 0],
            ['$pageview', 'post_cutover', 'recognized', 1, 0],
            ['evil@example.com', 'post_cutover', 'recognized', 1, 0],
            ['cta_click', 'private_period', 'recognized', 1, 0],
        ]
        for row in bad_rows:
            with self.subTest(row=row):
                self.assert_unavailable(monitor.summarize_cta_id_categories(payload([row])))

    def test_negative_non_integer_or_inconsistent_counts_fail_closed(self):
        bad_rows = [
            ['cta_click', 'post_cutover', 'recognized', -1, 0],
            ['cta_click', 'post_cutover', 'recognized', 1, -1],
            ['cta_click', 'post_cutover', 'recognized', '1', 0],
            ['cta_click', 'post_cutover', 'recognized', 1.0, 0],
            ['cta_click', 'post_cutover', 'recognized', True, 0],
            ['cta_click', 'post_cutover', 'recognized', None, 0],
            ['cta_click', 'post_cutover', 'recognized', 1, None],
            ['cta_click', 'post_cutover', 'recognized', 1, 2],
            ['cta_click', 'post_cutover', 'nonempty_unrecognized', 1, 1],
            ['cta_click', 'post_cutover', 'absent', 1, 1],
            ['cta_click', 'post_cutover', 'empty', 1, 1],
            ['cta_click', 'post_cutover', 'recognized', 0, 0],
        ]
        for row in bad_rows:
            with self.subTest(row=row):
                self.assert_unavailable(monitor.summarize_cta_id_categories(payload([row])))

    def test_duplicate_groups_or_unhashable_labels_fail_closed(self):
        rows = payload()['results']
        cases = [payload(rows + [list(rows[0])]),
                 payload([['cta_click', 'post_cutover', 'absent', 1, 0], ['cta_click', 'post_cutover', 'absent', 2, 0]]),
                 payload([['cta_click', [], 'recognized', 1, 0]]),
                 payload([[['private'], 'post_cutover', 'recognized', 1, 0]])]
        for case in cases:
            with self.subTest(case=case):
                self.assert_unavailable(monitor.summarize_cta_id_categories(case))


# Read-only result recorded for the rolling window ending 2026-10-26 02:00:18 UTC.
OBSERVED_ROWS = [
    ['affiliate_cta_click', 'post_cutover', 'recognized', 4, 0],
    ['affiliate_cta_click', 'post_cutover', 'nonempty_unrecognized', 1, 0],
]


class CollectionTests(unittest.TestCase):
    def collect(self, probe, cta_payload):
        site = site_fixtures.SiteScopeTests.payload(None)

        def posthog(_key, query):
            if query == monitor.host_parser_probe_query():
                return probe
            if 'AS host_bucket' in query:
                return site
            if 'AS cta_id_category' in query:
                return cta_payload
            if query.startswith('SELECT event, count()'):
                return {'columns': ['event', 'total'], 'results': [['$pageview', 47], ['affiliate_cta_click', 5]]}
            return {'columns': monitor.BASELINE_COLUMNS, 'results': [
                ['/', 'affiliate_cta_click', 'post_cutover', 'final_cta', 'free_account', 5, 0, 0, 0, 0, 0]]}

        with ExitStack() as stack:
            stack.enter_context(patch.object(monitor, 'gsc_credentials', return_value=type('Credentials', (), {'token': 'test-token'})()))
            stack.enter_context(patch.object(monitor, 'gsc_query', return_value=[]))
            stack.enter_context(patch.object(monitor, 'inspect_url', return_value={}))
            stack.enter_context(patch.object(monitor, 'secret_value', return_value='test-secret'))
            stack.enter_context(patch.object(monitor, 'collect_referral_stats', return_value={'recent': {}, 'previous': {}, 'all_time': {}}))
            calls = stack.enter_context(patch.object(monitor, 'posthog_query', side_effect=posthog))
            result = monitor.collect(final_end=date(2026, 10, 23),
                                     collected_at=datetime(2026, 10, 26, 2, 0, 18, 500000, tzinfo=timezone.utc))
        return result, [call.args[1] for call in calls.call_args_list]

    def test_observed_fixed_window_attaches_to_rolling_instrumentation(self):
        result, queries = self.collect(site_fixtures.probe_payload(), payload(OBSERVED_ROWS))
        instrumentation = result['posthog']['instrumentation']
        self.assertEqual(set(instrumentation), {'label', 'window', 'baseline', 'cta_id_categories', 'tracking_cutover_utc'})
        self.assertEqual(instrumentation['window']['start'], '2026-10-19T02:00:18+00:00')
        self.assertEqual(instrumentation['window']['end'], '2026-10-26T02:00:18+00:00')
        self.assertEqual(instrumentation['tracking_cutover_utc'], '2026-07-16 17:21:00Z')
        [cta_query] = [query for query in queries if 'AS cta_id_category' in query]
        self.assertEqual(cta_query, monitor.cta_id_category_query(instrumentation['window']))
        summary = instrumentation['cta_id_categories']
        self.assertEqual(summary['status'], 'available')
        self.assertEqual(summary['totals'], {'absent': 0, 'empty': 0, 'recognized': 4, 'nonempty_unrecognized': 1})
        self.assertEqual(summary['quiz_result']['total'], 0)
        self.assertEqual(summary['unknown']['total'], 1)
        self.assertIsNone(summary['unknown']['mapping'])
        self.assertEqual(summary['missing']['total'], 0)
        self.assertEqual(summary['scope'], monitor.POSTHOG_SCOPE)
        self.assertFalse(summary['hostname_filtered'])
        # Existing fields, aliases, gates and disabled rates are unchanged.
        self.assertEqual(instrumentation['baseline']['status'], 'available')
        self.assertEqual(result['posthog']['range'], 'last_7_days')
        self.assertEqual(result['posthog']['events']['results'], [['$pageview', 47], ['affiliate_cta_click', 5]])
        self.assertEqual(result['posthog']['affiliate_breakdown']['results'],
                         [['/', 'final_cta', 'free_account', 5, 'post_cutover']])
        self.assertEqual(result['posthog']['site_scope']['parser']['status'], 'verified')
        self.assertEqual(result['posthog']['site_scope']['recent']['status'], 'available')
        self.assertFalse(result['comparability']['cross_source_rates_enabled'])
        self.assertIsNone(result['comparability']['rates'])

    def test_cta_query_runs_independently_of_parser_gate_and_failure_is_isolated(self):
        result, queries = self.collect({'incomplete': True}, {'incomplete': True})
        self.assertFalse(any('AS host_bucket' in query for query in queries))
        self.assertEqual(result['posthog']['site_scope']['recent']['status'], 'unavailable')
        summary = result['posthog']['instrumentation']['cta_id_categories']
        self.assertEqual(summary['status'], 'unavailable')
        self.assertIsNone(summary['totals'])
        self.assertEqual(summary['scope'], monitor.POSTHOG_SCOPE)
        self.assertEqual(result['posthog']['events']['status'], 'available')
        self.assertEqual(result['posthog']['instrumentation']['baseline']['status'], 'available')


if __name__ == '__main__':
    unittest.main()
