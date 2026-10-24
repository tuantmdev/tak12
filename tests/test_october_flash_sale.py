import hashlib
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "https://tak12.com/news/n/2525/"
    "uu-dai-thang-10-giam-15-toan-bo-goi-tang-azvocab-va-qua-tang-cho-vao-6"
)


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class OctoberFlashSaleTests(unittest.TestCase):
    def test_verified_flash_sale_is_coordinated_and_expires(self):
        ctas = []
        for path, section_id, prefix in [
            ("index.html", "homepage-oct26", "homepage"),
            ("tak12-ma-giam-gia/index.html", "oct26", "coupon_guide"),
        ]:
            html = (ROOT / path).read_text(encoding="utf-8")
            match = re.search(
                rf'<section\b[^>]*id="{section_id}"[^>]*>.*?</section>', html, re.S
            )
            self.assertIsNotNone(match, f"Missing OCT26 section in {path}")
            section = match.group()
            tags = Tags(section).tags
            attrs = tags[0][1]
            self.assertIn("hidden", attrs, "No-JS visits must keep dated offers hidden")
            self.assertIn("data-dated-offer", attrs)
            self.assertEqual("31/10/2026", attrs["data-end-date"])
            for fact in [
                "20/10", "23h59 ngày 31/10/2026", "giờ việt nam", "oct26",
                "giảm 15%", "mọi gói ôn luyện", "01 năm azvocab pro",
                "490.000đ", "mỗi lần mua chỉ áp dụng 01 mã học bổng",
                "kiểm tra số tiền cuối cùng trước khi trả",
            ]:
                self.assertIn(fact, section.lower())
            links = [a for tag, a in tags if tag == "a"]
            expected = [
                (
                    f"{prefix}_oct26_pricing",
                    "https://tak12.com/info/bang-gia?ref=njg2odn",
                    "campaign",
                ),
                (
                    f"{prefix}_oct26_source",
                    SOURCE + "?ref=njg2odn",
                    "verify-offer-terms",
                ),
            ]
            for cta, href, intent in expected:
                link = next(a for a in links if a.get("data-cta") == cta)
                self.assertEqual(href, link["href"])
                self.assertEqual("_blank", link["target"])
                self.assertEqual({"sponsored", "noopener"}, set(link["rel"].split()))
                self.assertEqual(intent, link["data-intent"])
                ctas.append(cta)
            self.assertNotIn("affiliate-disclosure", section)
            self.assertNotIn("data-affiliate-disclosure", section)
            for marker in ["OCT26", "15%", "490.000đ"]:
                self.assertNotIn(marker, html.split("</head>")[0])
                for schema in re.findall(
                    r'<script\b[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                    html,
                    re.S,
                ):
                    json.loads(schema)
                    self.assertNotIn(marker, schema)
        self.assertEqual(len(ctas), len(set(ctas)))

        llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
        for fact in [
            "OCT26",
            "20/10 đến 23:59 ngày 31/10/2026",
            "giảm 15%",
            "01 năm azVocab PRO",
            "490.000 đồng",
            "Mỗi lần mua chỉ áp dụng 01 mã học bổng",
            SOURCE,
        ]:
            self.assertIn(fact, llms)
        self.assertIn("Sau thời điểm này, thông tin chỉ có giá trị lịch sử", llms)
        self.assertIn("https://tak12.com/info/bang-gia?ref=njg2odn", llms)

        contract = json.loads((ROOT / "sitemap-content.json").read_text())
        for url, page in [
            ("https://tak-12.com/", ROOT / "index.html"),
            ("https://tak-12.com/tak12-ma-giam-gia/", ROOT / "tak12-ma-giam-gia/index.html"),
        ]:
            self.assertEqual("2026-10-23", contract[url]["lastmod"])
            self.assertEqual(hashlib.sha256(page.read_bytes()).hexdigest(), contract[url]["sha256"])


if __name__ == "__main__":
    unittest.main()
