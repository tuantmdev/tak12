"""Issue #19 contracts: exact-hostname site scope, completeness, unavailable organic cohort."""
import json
import sys
import unittest
from contextlib import ExitStack
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tak12_monitor as monitor


def probe_payload(overrides=None):
    observed = {label: expected for label, _url, expected in monitor.HOST_PARSER_CASES}
    observed.update(overrides or {})
    labels = [label for label, _url, _expected in monitor.HOST_PARSER_CASES]
    return {'columns': labels, 'results': [[observed[label] for label in labels]]}


class HostParserTests(unittest.TestCase):
    def test_allowlist_is_exact_and_buckets_are_fixed(self):
        self.assertEqual(monitor.SITE_HOSTNAMES, ('tak-12.com',))
        self.assertEqual(monitor.HOST_BUCKETS, ('site', 'unknown', 'other_host'))

    def test_adversarial_cases_cover_spoofs_wrong_hosts_and_missing_urls(self):
        expected = {label: bucket for label, _url, bucket in monitor.HOST_PARSER_CASES}
        for label in ('userinfo_spoof', 'userinfo_before_site', 'suffix_spoof', 'prefix_spoof',
                      'host_in_path', 'host_in_query', 'scheme_less', 'path_only', 'missing'):
            self.assertIn(label, expected)
        self.assertEqual(expected['site_root'], 'site')
        self.assertEqual(expected['site_uppercase'], 'site')
        for label in ('suffix_spoof', 'prefix_spoof', 'www_subdomain', 'host_in_path',
                      'host_in_query', 'localhost_test'):
            self.assertEqual(expected[label], 'other_host', label)
        for label in ('userinfo_spoof', 'userinfo_before_site', 'scheme_less', 'path_only',
                      'missing', 'whitespace', 'non_http_scheme', 'empty_authority'):
            self.assertEqual(expected[label], 'unknown', label)

    def test_expression_parses_hostname_not_pathname(self):
        expression = monitor.host_bucket_expression('properties.$current_url')
        self.assertIn('domain(', expression)
        self.assertIn("'tak-12.com'", expression)
        self.assertNotIn('pathname', expression)
        self.assertNotIn('$host', expression)
        self.assertNotIn('LIKE', expression.upper())
        self.assertNotIn('endsWith', expression)

    def test_probe_queries_only_literals_never_events(self):
        query = monitor.host_parser_probe_query()
        self.assertNotIn('FROM', query.upper())
        for label, url, _expected in monitor.HOST_PARSER_CASES:
            self.assertIn(' AS ' + label, query)

    def test_probe_literals_are_escaped(self):
        self.assertEqual(monitor.hogql_string("a'b\\c"), "'a\\'b\\\\c'")

    def test_matching_probe_verifies_parser(self):
        result = monitor.summarize_host_parser(probe_payload())
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(result['mismatched_cases'], [])
        self.assertEqual(result['cases'], len(monitor.HOST_PARSER_CASES))

    def test_spoof_misclassification_fails_closed_without_echoing_values(self):
        result = monitor.summarize_host_parser(probe_payload({'userinfo_spoof': 'site', 'suffix_spoof': 'evil.example'}))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(sorted(result['mismatched_cases']), ['suffix_spoof', 'userinfo_spoof'])
        self.assertNotIn('evil.example', json.dumps(result))

    def test_unavailable_or_malformed_probe_is_not_verified(self):
        cases = [None, {}, {'incomplete': True}, {**probe_payload(), 'hasMore': True},
                 {**probe_payload(), 'error': 'private'}, {'columns': ['site_root'], 'results': [['site']]},
                 {**probe_payload(), 'results': []}, {**probe_payload(), 'results': [[None]]}]
        for payload in cases:
            result = monitor.summarize_host_parser(payload)
            self.assertNotEqual(result['status'], 'verified')
            self.assertNotIn('private', json.dumps(result))


VERIFIED = {'status': 'verified', 'cases': len(monitor.HOST_PARSER_CASES), 'mismatched_cases': []}


class SiteScopeTests(unittest.TestCase):
    def window(self):
        return monitor.calendar_windows(date(2026, 10, 16))['recent']

    def payload(self):
        return {'columns': monitor.SITE_SCOPE_COLUMNS, 'results': [
            ['site', '$pageview', 60, 0, 0, 0, 0, 0, 60],
            ['unknown', '$pageview', 5, 5, 5, 5, 5, 5, 5],
            ['other_host', '$pageview', 2, 0, 0, 0, 0, 0, 2],
            ['site', 'affiliate_cta_click', 12, 0, 0, 0, 0, 0, 12],
        ]}

    def test_query_uses_exact_bounds_fixed_labels_and_no_raw_values(self):
        query = monitor.site_scope_query(self.window())
        self.assertIn("timestamp >= toDateTime('2026-10-10 07:00:00', 'UTC')", query)
        self.assertIn("timestamp < toDateTime('2026-10-17 07:00:00', 'UTC')", query)
        self.assertIn(monitor.host_bucket_expression('properties.$current_url') + ' AS host_bucket', query)
        self.assertIn('GROUP BY host_bucket, event', query)
        for column in monitor.SITE_SCOPE_COLUMNS[3:]:
            self.assertIn(' AS ' + column, query)
        for forbidden in ('distinct_id', 'person', 'now()', 'properties.$current_url AS',
                          'properties.$referrer AS', 'properties.$host AS', 'uniq', 'groupArray', 'any('):
            self.assertNotIn(forbidden, query)
        self.assertIn(f'LIMIT {monitor.AGGREGATE_ROW_LIMIT}', query)

    def test_site_unknown_other_host_totals_and_completeness(self):
        result = monitor.summarize_site_scope(self.payload(), VERIFIED)
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['buckets']['site'], {'$pageview': 60, 'affiliate_cta_click': 12, 'cta_click': 0})
        self.assertEqual(result['buckets']['unknown']['$pageview'], 5)
        self.assertEqual(result['buckets']['other_host']['$pageview'], 2)
        self.assertEqual(result['totals'], {'$pageview': 67, 'affiliate_cta_click': 12, 'cta_click': 0})
        pageview = result['completeness']['$pageview']
        self.assertEqual(pageview['total'], 67)
        self.assertEqual(pageview['missing']['$current_url'], 5)
        self.assertEqual(pageview['missing']['utm_source'], 67)
        self.assertFalse(pageview['complete']['utm_source'])
        self.assertTrue(result['completeness']['affiliate_cta_click']['complete']['$session_id'])
        self.assertEqual(result['counts_unit'], 'events, not users/sessions')

    def test_organic_counts_are_explicitly_unavailable(self):
        for parser in (VERIFIED, {'status': 'failed'}):
            result = monitor.summarize_site_scope(self.payload(), parser)
            self.assertEqual(result['organic']['status'], 'unavailable')
            self.assertIsNone(result['organic']['counts'])
            self.assertEqual(result['attribution_status']['organic'], 'unavailable')
        self.assertEqual(monitor.summarize_site_scope(self.payload(), VERIFIED)['attribution_status']['site_only'],
                         'hostname_filtered_events')

    def test_valid_empty_window_is_zero_not_missing(self):
        result = monitor.summarize_site_scope({'columns': monitor.SITE_SCOPE_COLUMNS, 'results': []}, VERIFIED)
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['buckets']['site']['$pageview'], 0)
        self.assertEqual(result['completeness']['$pageview']['total'], 0)

    def test_unverified_parser_fails_closed(self):
        for parser in ({'status': 'failed', 'mismatched_cases': ['userinfo_spoof']}, {'status': 'unavailable'}, None):
            result = monitor.summarize_site_scope(self.payload(), parser)
            self.assertEqual(result['status'], 'unavailable')
            self.assertIsNone(result['buckets'])
            self.assertIsNone(result['totals'])

    def test_incomplete_malformed_or_unexpected_rows_fail_closed(self):
        bad_rows = [
            ['evil.example', '$pageview', 1, 0, 0, 0, 0, 0, 0],
            ['site', 'private@example.com', 1, 0, 0, 0, 0, 0, 0],
            ['site', '$pageview', -1, 0, 0, 0, 0, 0, 0],
            ['site', '$pageview', '1', 0, 0, 0, 0, 0, 0],
            ['site', '$pageview', 1, 2, 0, 0, 0, 0, 0],
            ['site', '$pageview', 1, 0],
        ]
        cases = [None, {}, {'columns': [], 'results': []},
                 {**self.payload(), 'incomplete': True}, {**self.payload(), 'hasMore': True},
                 {**self.payload(), 'error': 'private server detail'},
                 {'columns': monitor.SITE_SCOPE_COLUMNS, 'results': self.payload()['results'] + [self.payload()['results'][0]]},
                 {'columns': monitor.SITE_SCOPE_COLUMNS, 'results': self.payload()['results'][:1] * monitor.AGGREGATE_ROW_LIMIT}]
        cases += [{'columns': monitor.SITE_SCOPE_COLUMNS, 'results': [row]} for row in bad_rows]
        for payload in cases:
            result = monitor.summarize_site_scope(payload, VERIFIED)
            self.assertEqual(result['status'], 'unavailable')
            self.assertIsNone(result['buckets'])
            text = json.dumps(result)
            self.assertNotIn('private', text)
            self.assertNotIn('evil.example', text)


class CollectionTests(unittest.TestCase):
    def collect(self, probe):
        site_rows = SiteScopeTests.payload(None)

        def posthog(_key, query):
            if query == monitor.host_parser_probe_query():
                return probe
            if 'AS host_bucket' in query:
                return site_rows
            if query.startswith('SELECT event, count()'):
                return {'columns': ['event', 'total'], 'results': [['$pageview', 47]]}
            return {'columns': monitor.BASELINE_COLUMNS, 'results': [['/', '$pageview', 'post_cutover', None, None, 67, 67, 0, 0, 0, 0]]}

        with ExitStack() as stack:
            stack.enter_context(patch.object(monitor, 'gsc_credentials', return_value=type('Credentials', (), {'token': 'test-token'})()))
            stack.enter_context(patch.object(monitor, 'gsc_query', return_value=[]))
            stack.enter_context(patch.object(monitor, 'inspect_url', return_value={}))
            stack.enter_context(patch.object(monitor, 'secret_value', return_value='test-secret'))
            stack.enter_context(patch.object(monitor, 'collect_referral_stats', return_value={'recent': {'clickCount': 44}, 'previous': {}, 'all_time': {}}))
            calls = stack.enter_context(patch.object(monitor, 'posthog_query', side_effect=posthog))
            result = monitor.collect(final_end=date(2026, 10, 16), collected_at=datetime(2026, 10, 19, tzinfo=timezone.utc))
        return result, [call.args[1] for call in calls.call_args_list]

    def test_stable_windows_gain_site_scope_without_changing_all_traffic(self):
        result, queries = self.collect(probe_payload())
        scope = result['posthog']['site_scope']
        self.assertEqual(scope['parser']['status'], 'verified')
        for name in ('recent', 'previous'):
            self.assertEqual(scope[name]['status'], 'available')
            self.assertEqual(scope[name]['buckets']['site']['$pageview'], 60)
            self.assertEqual(result['posthog']['stable'][name]['pages'][0]['pageviews'], 67)
        self.assertIn("timestamp >= toDateTime('2026-10-10 07:00:00', 'UTC')", queries[-2])
        self.assertIn("timestamp >= toDateTime('2026-10-03 07:00:00', 'UTC')", queries[-1])
        self.assertEqual(result['posthog']['events']['results'], [['$pageview', 47]])
        self.assertNotIn('site_scope', result['posthog']['instrumentation'])

    def test_contract_documents_rule_semantics_and_sources(self):
        contract = self.collect(probe_payload())[0]['posthog']['site_scope']['contract']
        self.assertEqual(contract['hostname_allowlist'], ['tak-12.com'])
        self.assertEqual(contract['url_property'], '$current_url')
        self.assertIn('event', contract['semantics']['counts'])
        self.assertIn('session', contract['semantics']['session'])
        self.assertIn('human', contract['semantics']['not_established'])
        self.assertIn('organic', contract['semantics']['not_established'])
        self.assertTrue(all(url.startswith('https://') for url in contract['documentation']))

    def test_failed_or_unavailable_parser_skips_site_queries_and_fails_closed(self):
        for probe in (probe_payload({'userinfo_spoof': 'site'}), {'incomplete': True}):
            result, queries = self.collect(probe)
            scope = result['posthog']['site_scope']
            self.assertNotEqual(scope['parser']['status'], 'verified')
            self.assertFalse(any('AS host_bucket' in query for query in queries))
            for name in ('recent', 'previous'):
                self.assertEqual(scope[name]['status'], 'unavailable')
                self.assertIsNone(scope[name]['organic']['counts'])
                self.assertEqual(result['posthog']['stable'][name]['status'], 'available')

    def test_site_scope_never_enables_cross_source_rates(self):
        result, _ = self.collect(probe_payload())
        self.assertFalse(result['comparability']['cross_source_rates_enabled'])
        self.assertIsNone(result['comparability']['rates'])
        self.assertTrue(any('organic' in reason for reason in result['comparability']['reasons']))


if __name__ == '__main__':
    unittest.main()
