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
        official_url = "https://tak12.com/info/dgnl-tieng-anh-toan-dau-nam?ref=njg2odn#chon-de-thi"

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

    def test_lop6_offer_leads_with_paid_eligibility_not_unconditional_free_claim(self):
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        detail = (ROOT / "tak12-on-thi-lop-6" / "index.html").read_text(encoding="utf-8")
        llms = (ROOT / "llms.txt").read_text(encoding="utf-8")

        for content in (homepage, detail, llms):
            self.assertIn("tặng kèm", content.lower())
            self.assertIn("còn hạn PRO", content)
        self.assertNotIn("Khóa luyện đề 3 môn miễn phí năm học 2027-2028", homepage)
        self.assertNotIn("một khóa luyện đề 3 môn **miễn phí**", llms)

    def test_active_november_combo_offer_is_coordinated_and_expires_fail_closed(self):
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        guide = (ROOT / "tak12-ma-giam-gia" / "index.html").read_text(encoding="utf-8")
        llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
        source = (ROOT / "docs" / "november-combo-source.md").read_text(encoding="utf-8")
        official = "https://tak12.com/news/n/2530/tang-toc-cuoi-hki-giam-30-combo-hoc-tot-va-nang-cao-toan-tieng-anh"

        for content, section_id in ((homepage, "homepage-november-combo"), (guide, "november-combo")):
            self.assertIn(f'id="{section_id}"', content)
            self.assertIn('data-dated-offer data-end-date="30/11/2026" hidden', content)
            self.assertIn("Giảm trực tiếp 30%", content)
            self.assertIn("Combo Học tốt &amp; Nâng cao Toán – Tiếng Anh", content)
            self.assertIn("thời hạn 1 năm", content)
            self.assertIn(official + "?ref=njg2odn", content)
        self.assertIn('data-cta="homepage_november_combo_pricing" data-intent="campaign-pricing"', homepage)
        self.assertIn('data-cta="coupon_guide_november_combo_pricing" data-intent="campaign-pricing"', guide)
        self.assertIn('rel="sponsored noopener"', homepage)
        self.assertIn("11/11 đến 30/11/2026", llms)
        self.assertIn(official + "?ref=njg2odn", llms)
        current_offer_heading = "## Ưu đãi đang có hiệu lực"
        lop6_heading = "## Chương trình ôn thi vào lớp 6 đang được TAK12 công bố"
        self.assertIn(current_offer_heading, llms)
        self.assertLess(llms.index(current_offer_heading), llms.index("11/11 đến 30/11/2026"))
        self.assertLess(llms.index("11/11 đến 30/11/2026"), llms.index(lop6_heading))
        self.assertIn("b51eab09854fb8bfbaf02d87e370b8c88952f6700cf84945aea7b7d4f289d071", source)


if __name__ == "__main__":
    unittest.main()
