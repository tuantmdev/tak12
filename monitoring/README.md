# TAK12 growth monitoring

Versioned source for the read-only TAK12 growth collector and watchdog used by the scheduled operator loop.

## Runtime

Secrets remain outside this repository:

- `~/.hermes/secrets/tak12-gsc-service-account.json` (mode `600`)
- `POSTHOG_API_KEY`, `TAK12_USERNAME`, `TAK12_PASSWORD`, and `TAK12_KC_SESSION` in `~/.hermes/.env`

Provision Chromium during installation or maintenance, separately from collection so a transient browser download failure cannot discard GSC/PostHog data:

```bash
./monitoring/provision_browser.sh
```

Run the collector through its dependency-declaring wrapper:

```bash
./monitoring/tak12_monitor.sh
```

Run the silent watchdog with the same declared dependencies:

```bash
uv run --with google-auth --with requests --with playwright \
  python monitoring/tak12_watchdog.py
```

The collector retries referral authentication at most once. Known authentication or browser-refresh failures return a sanitized `referral.status: unavailable` section while preserving independent GSC and PostHog results. Unexpected runtime errors remain fail-fast.

## Tests

```bash
uv run --with google-auth --with requests \
  python -m unittest discover -s monitoring/tests -v
bash -n monitoring/tak12_monitor.sh
```

The scheduled host copy may be installed from a reviewed revision, but credentials and refreshed session values must never be copied into this repository or command output.

## Reproducible baseline (issue #18)

`gsc.windows` and `posthog.windows` describe adjacent current (`recent`) and
`previous` calendar windows. Their local dates use `America/Los_Angeles` and
`[start, end)` bounds; PostHog queries use the corresponding literal UTC instants.
GSC API requests translate the exclusive end back to an inclusive `endDate`, as
specified in the [Search Console API reference](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).
`zoneinfo` handles both DST transitions: equal seven-day calendar windows can
have different elapsed hours. The default end remains three days before the UTC
collection date. `gsc.comparisons` includes 7-, 14-, and 28-day final comparisons.

`final_data_through` for GSC is the latest returned date containing final data,
not an assertion that every requested date has data. An empty date result leaves
it null; the requested final end is recorded separately. PostHog is an event
store with possible late arrivals, so its final-data-through is unknown/null.
Stable windows can be reproduced; late arrivals can still revise event totals.

`posthog.stable.recent` and `.previous` contain per-page pageview and CTA event
counts, CTA IDs/intents, and separate `cta_click` and `affiliate_cta_click` counts.
`schema_periods` and each CTA breakdown preserve the July 16, 2026 17:21 UTC
tracking cutover. Counts are events, not people or sessions. Pageview mapping uses
`source_page`, then `$pathname`, then the path of `$current_url`; fallback mapping
does not imply that the original `source_page` property exists. No user-level
rows, identifiers, raw URLs, referrers, or destination values are requested.

The versioned `report_dimensions.json` catalogue contains public paths, CTA IDs,
and intents from the site. It is a reporting allowlist, not a site change. Copy
it alongside `tak12_monitor.py` when installing the reviewed revision. Update it
when public labels change, retaining historical labels needed for comparisons.
Unknown labels become null buckets; their counts remain in totals and in
`unmapped_dimensions`. Missing/null/blank property counts are separate under
`missing`, by event type, for `source_page`, `cta_id`, `position`, `intent`, and
`destination_url` (CTA-only fields do not apply to pageviews). A supplied unknown
value is not counted as missing. `unmapped_source_page_events` includes events
that cannot be assigned to a known public path.

PostHog scope is project-wide all traffic; site-only and organic attribution are
unverified. `organic_attribution.counts` is null, never a fabricated zero or an
organic cohort inferred from GSC totals. Missing/malformed responses, incomplete
async queries, and potentially truncated results are unavailable, not zero.
The 50,000 aggregate-row safety limit also fails closed if reached.

`posthog.instrumentation` is separately labeled rolling seven-day monitoring,
anchored to one captured UTC collection timestamp. Compatibility keys `range`,
`events`, and `affiliate_breakdown` refer only to this rolling window. The watchdog
continues to use these rolling event counts; incomplete instrumentation produces
an unavailable status and no compatibility rows, preventing a partial response
from triggering a false missing-CTA alert. Stable reporting never uses `now()`.

`referral.windows` records the requested dates and explicitly unknown timezone,
boundary semantics, finality, and acquisition scope. `all_time` has null date
bounds. `site_only_attribution` is null: successful authentication does not verify
agent 210's scope. Existing referral counts and internal rates are preserved.
`comparability.cross_source_rates_enabled` remains false and `rates` null even
when every query succeeds. Date alignment alone cannot make search clicks,
all-traffic events, and agent-wide referral counts one cohort.

The observed October 12 run had rolling PostHog **47 pageviews / 5 affiliate CTA
events**, versus **51 / 6** for October 3–9 Los Angeles dates (October 3 07:00 UTC
inclusive to October 10 07:00 UTC exclusive). Referral **44 clicks / 2 signups /
0 orders** had unknown timezone/scope. These are historical issue evidence, not
assertions of current production counts. Do not calculate 6/18 or 2/6 as funnel
rates or infer CRO success from these samples.

## Site scope and attribution completeness (issue #19)

`posthog.site_scope` adds hostname-scoped totals for the same stable `recent` and
`previous` windows. It does not change `posthog.stable`, which remains all traffic.
Each window splits `$pageview`, `affiliate_cta_click` and `cta_click` event counts
into three fixed buckets; together they equal the all-traffic event totals:

- `site`: an `http(s)` `$current_url` where PostHog `domain()` and the literal URL
  authority (with any port removed) both equal `tak-12.com`, ignoring case. The
  allowlist is exact. `www.tak-12.com`, suffix or prefix lookalikes, and hosts
  that appear only in a path or query string do not count.
- `unknown`: the URL is missing or blank, path-only, scheme-less, not `http(s)`,
  has an empty authority or userinfo (`@`), or `domain()` and the authority
  disagree. The host is never taken from `$pathname`, `$host` or `source_page`.
- `other_host`: any other parsed host, including localhost, preview and test hosts.

The live check behind this rule found that PostHog `domain()` does not exclude
userinfo on its own. It returns `tak-12.com` for `https://x@tak-12.com/`. It also
accepts scheme-less input and returns empty for `localhost`. So `domain()` is
used only together with the checks above. `site_scope.parser` runs fixed literal
URLs (`HOST_PARSER_CASES`) through the same expression before any site query. If
any case lands in an unexpected bucket, or the probe is incomplete, no site
queries are sent and both windows are `unavailable`. Results show case labels
only, never values.

`completeness` counts missing or blank `$current_url`, `$host`, `$referrer`,
`$referring_domain`, `$session_id` and `utm_source` by event type. These are
presence counts only; no URL, referrer, host or identifier value is selected. The
counts are events, not users or sessions. Referrer and UTM properties belong to
each event. Session-level entry and channel attribution is not queried.
Hostname-filtered events do not prove human rather than bot traffic, and they do
not show organic acquisition. `organic.counts` is always null with status
`unavailable` because no verified acquisition contract exists. PostHog channel
types are a configurable rule list, not a verified contract for this site. Cross-
source rates remain disabled.

Field and function references: [PostHog default event properties](https://posthog.com/docs/data/events),
[sessions](https://posthog.com/docs/data/sessions),
[channel types](https://posthog.com/docs/data/channel-type),
[PostHog SQL functions](https://posthog.com/docs/sql/clickhouse-functions), and
[ClickHouse URL functions](https://clickhouse.com/docs/sql-reference/functions/url-functions).

Read-only verification on October 19, 2026 for October 10 07:00 to October 17
07:00 UTC: 25 of 25 parser cases matched. `site` had 67 pageview and 12
affiliate CTA events; `unknown` and `other_host` were both 0. That matched an
independent per-event count and the stable all-traffic page sum. Every event had
`$current_url`, `$host`, `$referrer`, `$referring_domain` and `$session_id`.
None had `utm_source` or `$utm_source`. The previous window, October 3 to
October 10, had `site` 51 pageview and 6 affiliate CTA events, with 0 in the
other buckets. These counts are evidence from that check, not fixed expectations.

## CTA ID diagnostics (issue #20)

`posthog.instrumentation.cta_id_categories` is a separate read-only aggregate
over the same rolling instrumentation window. It is added alongside the existing
instrumentation keys and does not change them, the `range`/`events`/
`affiliate_breakdown` aliases, the stable windows, the cutover split, the hostname
parser gate, or the disabled cross-source rates. It covers `affiliate_cta_click`
and `cta_click` events. Each event is placed in exactly one fixed category:

- `absent`: the `cta_id` property is missing or null.
- `empty`: present but empty or only ASCII whitespace (RE2 `[[:space:]]`).
- `recognized`: exactly equals an ID in `report_dimensions.json`. The match is
  case- and whitespace-sensitive, with no trimming or normalization.
- `nonempty_unrecognized`: any other supplied value. This is reported as
  `unknown` with `mapping: null`. It is never counted as missing and never mapped
  to a catalogue ID.

`missing` sums only `absent` and `empty`. `quiz_result` counts events whose ID is
exactly `quiz_result`, a recognized catalogue ID, by event type. Counts are split
by event and by `schema_periods` (pre/post the July 16, 2026 tracking cutover).
They are events, not users or sessions. Scope is project-wide all traffic
(`hostname_filtered: false`). The query does not use the site-scope parser gate
and runs whether or not the probe verifies. Only category labels, event names and
counts are selected. No `cta_id` value leaves PostHog, and the report contains none.

The summary fails closed. It is `unavailable` with null counts when the response
is missing, incomplete, errored, `hasMore` or at the 50,000-row limit. The same
applies to wrong columns, malformed or duplicate rows, unexpected labels, and
non-integer, negative or zero counts. It also applies when `quiz_result` exceeds
its row total or appears outside `recognized`. A valid empty response is zero.

A read-only aggregate run for the fixed rolling window from 2026-10-19 02:00:18
to 2026-10-26 02:00:18 UTC returned `recognized` 4, `nonempty_unrecognized` 1,
`absent` 0, `empty` 0 and `quiz_result` 0. The unrecognized ID is not known
from this aggregate. It is not mapped here, and no value was retrieved to
identify it. These are evidence from that run, not fixed expectations.

## Verification after authorized integration

This task does not activate the collector, alter cron, or perform production
interactions. GitHub Pages deployment does not activate monitoring. A read-only
check found the host wrapper targets `~/.hermes/scripts/tak12_monitor.py`, whose
contents differ from this workspace revision.

After integration is authorized, install the reviewed monitoring files (including
the catalogue) into the runtime target and compare their hashes to that revision.
Verify the scheduled command resolves to that target without editing schedules.
Then perform one real read-only collection with a fixed final end, using the
existing approved authentication flow and storing output only in a protected
runtime location. The Python entrypoint supports explicit windows:

```python
from datetime import date
from tak12_monitor import collect
report = collect(final_end=date(2026, 10, 9))
```

Use the real collection timestamp for instrumentation; tests can additionally
inject a timezone-aware `collected_at`. Independently run this aggregate query
against the same PostHog project, through approved credentials without printing
them, and reconcile the event totals with the sum of all stable page buckets,
including null buckets:

```sql
SELECT event, count() AS total
FROM events
WHERE timestamp >= toDateTime('2026-10-03 07:00:00', 'UTC')
  AND timestamp < toDateTime('2026-10-10 07:00:00', 'UTC')
  AND event IN ('$pageview', 'cta_click', 'affiliate_cta_click')
GROUP BY event
ORDER BY event
```

The same totals must also equal `site + unknown + other_host` in
`posthog.site_scope.<window>.totals`, with `site_scope.parser.status: verified`.
Verify available/partial statuses, per-page denominators, missing/unmapped counts,
cutover separation, and disabled cross-source rates. Record runtime revision,
window boundaries, aggregate reconciliation, and activation evidence without
credentials or user-level data. Recheck at the next weekly run; review seven-day
counts with denominators and the 14-/28-day final GSC comparisons. Any discrepancy
requires investigation, not a forced match to historical 51/6 totals.
