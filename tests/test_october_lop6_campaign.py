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

        # Keep only facts still present in the refreshed official announcement.
        public_surfaces = pages + [ROOT / "llms.txt"]
        for path in public_surfaces:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("23/01/2027", content)
            self.assertIn("18 buổi", content)

        self.assertIn(SOURCE, pages[0].read_text(encoding="utf-8"))
        self.assertIn(SOURCE, pages[1].read_text(encoding="utf-8"))

        contract = json.loads((ROOT / "sitemap-content.json").read_text())
        for url, path, expected_lastmod in [
            ("https://tak-12.com/", pages[0], "2026-11-18"),
            ("https://tak-12.com/tak12-on-thi-lop-6/", pages[1], "2026-11-16"),
        ]:
            self.assertEqual(expected_lastmod, contract[url]["lastmod"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), contract[url]["sha256"])


if __name__ == "__main__":
    unittest.main()
