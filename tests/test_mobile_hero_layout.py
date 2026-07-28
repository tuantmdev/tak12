import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STYLES = ROOT / "styles.css"


class MobileHeroLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = STYLES.read_text(encoding="utf-8")
        mobile_match = re.search(
            r"@media \(max-width: 640px\) \{(?P<rules>.*?)\n\}",
            cls.css,
            re.DOTALL,
        )
        cls.mobile_rules = mobile_match.group("rules") if mobile_match else ""

    def test_mobile_hero_actions_stack_into_full_width_tap_targets(self):
        self.assertRegex(
            self.mobile_rules,
            r"\.hero-actions\s*\{[^}]*flex-direction:\s*column;",
        )
        self.assertRegex(
            self.mobile_rules,
            r"\.hero-actions\s+\.btn\s*\{[^}]*width:\s*100%;",
        )
        self.assertNotRegex(
            self.mobile_rules,
            r"\.hero-actions\s+\.btn\s*\{[^}]*flex:\s*1;",
        )

    def test_mobile_hero_uses_compact_vertical_spacing(self):
        self.assertRegex(
            self.mobile_rules,
            r"\.hero\s*\{[^}]*padding:\s*40px\s+0\s+44px;",
        )


if __name__ == "__main__":
    unittest.main()
