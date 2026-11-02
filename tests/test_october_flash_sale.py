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
    def test_expired_flash_sale_is_removed_from_all_public_surfaces(self):
        pages = [ROOT / "index.html", ROOT / "tak12-ma-giam-gia/index.html"]
        llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
        for content in [*(page.read_text(encoding="utf-8") for page in pages), llms]:
            for marker in ["OCT26", "homepage-oct26", 'id="oct26"', "490.000", SOURCE]:
                self.assertNotIn(marker, content)

        contract = json.loads((ROOT / "sitemap-content.json").read_text())
        for url, page, expected_lastmod in [
            ("https://tak-12.com/", pages[0], "2026-11-02"),
            ("https://tak-12.com/tak12-ma-giam-gia/", pages[1], "2026-11-01"),
        ]:
            self.assertEqual(expected_lastmod, contract[url]["lastmod"])
            self.assertEqual(hashlib.sha256(page.read_bytes()).hexdigest(), contract[url]["sha256"])


if __name__ == "__main__":
    unittest.main()
