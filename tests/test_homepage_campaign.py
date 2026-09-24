import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class HomepageCampaignTests(unittest.TestCase):
    def test_homepage_keeps_evergreen_search_positioning_after_campaign_removal(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        tags = Tags(html).tags

        for key, value in [("name", "description"), ("property", "og:description"), ("name", "twitter:description")]:
            meta = next(a for t, a in tags if t == "meta" and a.get(key) == value)
            self.assertIn("mã giảm giá TAK12", meta["content"])
            self.assertIn("mã học bổng", meta["content"])
            self.assertNotIn("20%", meta["content"])
        self.assertIn("<title>TAK12: Đánh Giá Độc Lập &amp; Chọn Chương Trình</title>", html)

    def test_homepage_has_no_expired_campaign_slot_or_ctas(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for marker in [
            'id="homepage-nsy2627"',
            'data-cta="homepage_nsy2627_pricing"',
            'data-cta="homepage_nsy2627_source"',
            "/tak12-ma-giam-gia/#nsy2627",
            "NSY2627",
            "20/09/2026",
        ]:
            self.assertNotIn(marker, html)

    def test_current_free_assessment_is_coordinated_across_campaign_surfaces(self):
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        guide = (ROOT / "tak12-ma-giam-gia" / "index.html").read_text(encoding="utf-8")
        llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
        official_url = "https://tak12.com/info/dgnl-tieng-anh-toan-dau-nam?ref=njg2odn"

        self.assertIn('id="homepage-free-assessment"', homepage)
        self.assertIn(
            f'href="{official_url}" target="_blank" rel="sponsored noopener" '
            'data-cta="homepage_free_assessment" data-intent="free_assessment"',
            homepage,
        )
        self.assertIn("Đánh giá năng lực đầu năm miễn phí", homepage)
        self.assertIn('id="dgnl-dau-nam"', guide)
        self.assertIn(
            f'href="{official_url}" target="_blank" rel="sponsored noopener" '
            'data-cta="coupon_guide_free_assessment" data-intent="free_assessment"',
            guide,
        )
        self.assertIn(official_url, llms)
        self.assertNotIn("Back to School", llms, "Keep LLM collateral useful after seasonal wording ages")


if __name__ == "__main__":
    unittest.main()
