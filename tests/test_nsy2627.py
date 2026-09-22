import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExpiredCampaignTests(unittest.TestCase):
    def test_expired_campaign_is_removed_from_every_published_surface(self):
        published = sorted(ROOT.rglob("*.html")) + [
            ROOT / "llms.txt",
            ROOT / "docs/keyword-map.md",
        ]
        retired_markers = [
            "NSY2627",
            "homepage-nsy2627",
            'id="nsy2627"',
            "20/09/2026",
            "campaign_nsy2627",
            "/news/n/2486/",
        ]

        for path in published:
            content = path.read_text(encoding="utf-8")
            for marker in retired_markers:
                self.assertNotIn(marker, content, f"Expired campaign marker {marker!r} remains in {path}")

    def test_campaign_evidence_remains_archived_with_provenance(self):
        source_image = ROOT / "docs/nsy2627-top-packages.jpg"
        source_notes = (ROOT / "docs/nsy2627-source.md").read_text(encoding="utf-8")

        self.assertTrue(source_image.is_file(), "Owner-supplied campaign evidence must remain archived")
        checksum = hashlib.sha256(source_image.read_bytes()).hexdigest()
        self.assertEqual("e319f8e9d96839355557a2a9a91fe064364ae7ac9b567f9f25a9aeadcebf8b2c", checksum)
        self.assertIn("owner supplied", source_notes.lower())
        self.assertIn(checksum, source_notes)
        self.assertIn("20/09/2026", source_notes)

    def test_commercial_guide_keeps_date_neutral_code_validation_help(self):
        html = (ROOT / "tak12-ma-giam-gia/index.html").read_text(encoding="utf-8")

        normalized = html.casefold()
        for marker in [
            "Cách kiểm tra mã giảm giá và mã học bổng TAK12 hiện hành",
            "thời hạn",
            "phạm vi áp dụng",
            "số tiền cuối cùng",
            "không sử dụng mã cũ",
        ]:
            self.assertIn(marker.casefold(), normalized)
        self.assertIn('href="https://tak12.com/info/bang-gia?ref=njg2odn"', html)
        self.assertIn('data-cta="coupon_current_code_check"', html)
        self.assertIn('data-intent="verify-current-price-and-access"', html)


if __name__ == "__main__":
    unittest.main()
