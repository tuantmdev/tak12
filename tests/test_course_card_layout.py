import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STYLESHEET = ROOT / "styles.css"


class CourseCardLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = STYLESHEET.read_text(encoding="utf-8")

    def test_desktop_course_cards_anchor_price_and_cta_to_a_shared_bottom_row(self):
        card_rule = re.search(r"\.course-card\s*\{([^}]*)\}", self.css, re.S)
        self.assertIsNotNone(card_rule)
        declarations = card_rule.group(1) if card_rule else ""
        self.assertRegex(declarations, r"display\s*:\s*flex\s*;")
        self.assertRegex(declarations, r"flex-direction\s*:\s*column\s*;")
        self.assertRegex(
            self.css,
            r"\.course-card\s+\.price-row\s*\{[^}]*margin-top\s*:\s*auto\s*;[^}]*\}",
        )


if __name__ == "__main__":
    unittest.main()
