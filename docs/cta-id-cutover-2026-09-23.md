# CTA ID cutover — 2026-09-23

Affiliate click analytics keep the existing `affiliate_cta_click` event and `source_page`, `position`, `intent`, and `destination_url` properties. On 2026-09-23, repeated CTA IDs were replaced with page-and-placement-specific IDs so each monetized placement can be analyzed without relying on `source_page` to disambiguate it.

For comparisons spanning the cutover, query the legacy and replacement IDs separately. Do not combine them without also segmenting by `source_page`.

| Legacy ID | Replacement IDs |
| --- | --- |
| `nav_cta` | `cambridge_nav_free_account`, `school_support_nav_free_account`, `ielts_nav_free_account`, `lop6_nav_free_account`, `lop10_nav_free_account`, `coupon_guide_nav_free_account`, `thpt_nav_free_account` |
| `top_banner_signup` | `ielts_top_banner_free_account`, `lop6_top_banner_free_account`, `lop10_top_banner_free_account`, `coupon_guide_top_banner_free_account` |
| `lp_coupon_inline` | `ielts_inline_free_account`, `lop6_inline_free_account`, `lop10_inline_free_account` |
| `coupon_wrap_signup` | `ielts_coupon_free_account`, `lop6_coupon_free_account`, `lop10_coupon_free_account`, `coupon_guide_bottom_free_account` |
