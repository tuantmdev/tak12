# TAK12 keyword ownership — scoped campaign update

## Evergreen homepage intent
- URL: https://tak-12.com/
- Primary: TAK12, đánh giá TAK12, chọn chương trình TAK12.
- Preserve title, H1, canonical and existing course/review routes. Description and social descriptions mention checking mã học bổng and PRO conditions without advertising a permanent discount.

## Commercial guide ownership
- URL: https://tak-12.com/tak12-ma-giam-gia/
- Primary commercial intent: mã giảm giá TAK12, mã học bổng TAK12, FREE và PRO, cách nhập mã TAK12.
- Keep the detailed redemption guide here; homepage is a short discovery/conversion surface, not a duplicate guide.

## Dated supporting campaign
- Homepage slot: https://tak-12.com/#homepage-nsy2627
- Detailed guide: https://tak-12.com/tak12-ma-giam-gia/#nsy2627
- Supporting phrases: NSY2627, ưu đãi TAK12 năm học mới 2026–2027, giảm 20% gói PRO.
- Valid through 20/09/2026 Vietnam time; expires exclusively at 2026-09-21T00:00:00+07:00. Excludes Speaking/Writing credit packages.
- Source and verification: docs/nsy2627-source.md. llms.txt carries the dated source, exception and explicit historical-only interpretation after expiry.
- Both visible campaign sections use the existing Vietnam-time expiry handler, hidden without JS and after expiry. No Offer schema or time-limited claim in evergreen title/meta descriptions. Static source remains dated, not a claim of ongoing eligibility.
- Keyword mapping is an editorial ownership contract, not a ranking guarantee; do not stuff meta keywords or retarget the homepage's core intent.

## Measurement
Compare homepage_nsy2627_pricing and homepage_nsy2627_source affiliate_cta_click events after deployment, segmented by source_page and position. Existing analytics.js supplies destination_url and intent. Do not mix pre-release events or infer sales from CTA clicks.
