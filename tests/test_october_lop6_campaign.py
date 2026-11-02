import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://tak12.com/news/n/2499/tang-khoa-luyen-de-vao-6-cho-hoc-vien-tak12"


class OctoberLop6CampaignTests(unittest.TestCase):
    def test_expired_october_offer_is_removed_from_public_pages(self):
        pages = [ROOT / "index.html", ROOT / "tak12-on-thi-lop-6/index.html"]
        for path in pages:
            html = path.read_text(encoding="utf-8")
            for marker in [
                "homepage-october-lop6",
                'id="october-lop6"',
                "lop6_october_lop6_pricing",
                "lop6_october_lop6_source",
            ]:
                self.assertNotIn(marker, html)

        # Keep the separately verified November course announcement and its source.
        self.assertIn(SOURCE, pages[0].read_text(encoding="utf-8"))
        self.assertIn(SOURCE, pages[1].read_text(encoding="utf-8"))

        contract = json.loads((ROOT / "sitemap-content.json").read_text())
        for url, path in [
            ("https://tak-12.com/", pages[0]),
            ("https://tak-12.com/tak12-on-thi-lop-6/", pages[1]),
        ]:
            self.assertEqual("2026-11-02", contract[url]["lastmod"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), contract[url]["sha256"])


if __name__ == "__main__":
    unittest.main()
