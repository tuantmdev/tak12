# NSY2627 source and release scope

Verified on 2026-09-10 from the rendered official TAK12 announcement:
https://tak12.com/news/n/2486/chao-mung-nam-hoc-moi-26-27-tang-ma-giam-20-va-thoi-han-pro?ref=njg2odn

The announcement (dated 5/9/2026) states:
- Code NSY2627 reduces all PRO learning packages by 20% through the end of 20/09/2026.
- Speaking/Writing credit (xu) packages are excluded.
- Eligible international-English combos from one year receive additional duration, credited on 21/09/2026.

We do not reproduce package prices or infer eligibility beyond the source. The owner supplied the redemption walkthrough; users perform registration, captcha and payment themselves. No registration or purchase was performed for this release.

## Narrow scope

Only the existing /tak12-ma-giam-gia/ commercial page gets campaign content, below its unchanged hero. Homepage HTML, search metadata, canonical, FAQ and existing referral links remain unchanged. No time-limited Offer schema or claim is added to evergreen metadata.

Reuse the existing countdown with an exclusive expiry of 2026-09-21T00:00:00+07:00 (2026-09-20T17:00:00Z), independent of visitor timezone. A hidden-by-default section is revealed only after validation; expired or no-JavaScript visits retain the evergreen page and pricing CTA. Visibility/pageshow and scheduled ticks handle long-open tabs. Static HTML retains dated historical source text; the rendered promotional section is hidden after expiry, not removed by a scheduled build.

Owner policy intentionally omits the visible affiliate-disclosure banner. All compensated links retain sponsored/noopener and explicit CTA tracking. Machine-readable sponsored semantics do not necessarily replace visible disclosure in every jurisdiction; legal/compliance review remains advisable.

## Checks

- Baseline: `python -m unittest discover -s tests -q` (63 passed).
- TDD: campaign contract failed for missing section, then passed; browser behavior failed for hidden active offer before JS wiring, then passed.
- Full static suite: `python -m unittest discover -s tests -q`.
- Browser: `node tests/nsy2627.browser.cjs` (requires Playwright and Chromium). Exercises Asia/Ho_Chi_Minh, America/Los_Angeles, Pacific/Auckland; final valid millisecond, midnight expiry, long-open tab, reload and no-JS fallback. HTTPS is blocked for local tests to avoid synthetic analytics traffic.
- `git diff --check`; independent review and exact-SHA deployment/live checks before completion report.
