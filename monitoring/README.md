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

Verify available/partial statuses, per-page denominators, missing/unmapped counts,
cutover separation, and disabled cross-source rates. Record runtime revision,
window boundaries, aggregate reconciliation, and activation evidence without
credentials or user-level data. Recheck at the next weekly run; review seven-day
counts with denominators and the 14-/28-day final GSC comparisons. Any discrepancy
requires investigation, not a forced match to historical 51/6 totals.
