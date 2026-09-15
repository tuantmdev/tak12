# NSY2627 source and release scope

Verified on 2026-09-10 from the rendered official TAK12 announcement:
https://tak12.com/news/n/2486/chao-mung-nam-hoc-moi-26-27-tang-ma-giam-20-va-thoi-han-pro?ref=njg2odn

The announcement (dated 5/9/2026) states:
- Code NSY2627 reduces all PRO learning packages by 20% through the end of 20/09/2026.
- Speaking/Writing credit (xu) packages are excluded.
- Eligible international-English combos from one year receive additional duration, credited on 21/09/2026.

On 2026-09-15, the owner supplied TAK12's accompanying “Top gói ôn luyện dẫn đầu xu hướng đầu năm học 2026–2027” copy and campaign graphic. The source graphic is preserved at [nsy2627-top-packages.jpg](nsy2627-top-packages.jpg) (SHA-256 `e319f8e9d96839355557a2a9a91fe064364ae7ac9b567f9f25a9aeadcebf8b2c`). They identify six packages, their original and post-code prices, duration or access end date, and monthly equivalents where relevant. The dated campaign section reproduces these package facts but keeps them out of evergreen metadata and course pages. Users are told to recheck the live price, duration and package contents before paying. The owner also supplied the redemption walkthrough; users perform registration, captcha and payment themselves. No registration or purchase was performed for this release.

Package facts supplied on 2026-09-15:
- International English Certificates, 1 year: 890,000đ → 712,000đ; 13 months; approximately 55,000đ/month.
- International English Certificates, 5 years: 2,290,000đ → 1,832,000đ; 65 months; approximately 28,000đ/month.
- English FULL A2–C1, 4 years: 3,250,000đ → 2,600,000đ; 52 months; 50,000đ/month.
- English FULL A1–C1, 5 years: 3,680,000đ → 2,944,000đ; 65 months; approximately 45,000đ/month.
- Grade 6 entrance preparation for Grade 5: 2,850,000đ → 2,280,000đ; access through 30/06/2027.
- Grade 6 entrance preparation for Grade 4: 3,620,000đ → 2,896,000đ; access through 30/06/2028.

## Narrow scope

The initial release covered /tak12-ma-giam-gia/. Following explicit user correction, the homepage also restores its existing campaign slot between the unchanged hero and featured courses, reusing campaign CSS and the dated-offer expiry handler. It includes code, expiry, credit exception, attributed pricing/source CTAs and a guide link. Homepage title, H1, canonical, FAQ and existing referral links remain unchanged; only description/social descriptions gain evergreen code-checking guidance. llms.txt records sourced, explicitly dated campaign facts with historical-only interpretation after expiry. docs/keyword-map.md assigns detailed coupon intent to the guide and supporting seasonal discovery to the homepage. No time-limited Offer schema or claim is added to evergreen metadata.

Reuse the existing countdown with an exclusive expiry of 2026-09-21T00:00:00+07:00 (2026-09-20T17:00:00Z), independent of visitor timezone. A hidden-by-default section is revealed only after validation; expired or no-JavaScript visits retain the evergreen page and pricing CTA. Visibility/pageshow and scheduled ticks handle long-open tabs. Static HTML retains dated historical source text; the rendered promotional section is hidden after expiry, not removed by a scheduled build.

Owner policy intentionally omits the visible affiliate-disclosure banner. All compensated links retain sponsored/noopener and explicit CTA tracking. Machine-readable sponsored semantics do not necessarily replace visible disclosure in every jurisdiction; legal/compliance review remains advisable.

## Checks

- Baseline: `python -m unittest discover -s tests -q` (63 passed).
- TDD: campaign contract failed for missing section, then passed; browser behavior failed for hidden active offer before JS wiring, then passed.
- Full static suite: `python -m unittest discover -s tests -q`.
- Browser: `node tests/nsy2627.browser.cjs` (requires Playwright and Chromium). Exercises Asia/Ho_Chi_Minh, America/Los_Angeles, Pacific/Auckland; final valid millisecond, midnight expiry, long-open tab, reload and no-JS fallback. HTTPS is blocked for local tests to avoid synthetic analytics traffic.
- `git diff --check`; independent review and exact-SHA deployment/live checks before completion report.
