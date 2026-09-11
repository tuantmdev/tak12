import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HomepageCampaignLayoutTests(unittest.TestCase):
    def test_featured_campaign_uses_semantic_hierarchy(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        section = html[html.index('id="homepage-nsy2627"'):html.index('id="courses-section"')]
        self.assertIn('class="campaign-carousel campaign-featured"', section)
        self.assertIn('class="campaign-eyebrow"', section)
        self.assertIn('class="campaign-code-card" role="group" aria-labelledby="homepage-nsy2627-code-label"', section)
        self.assertIn('<span class="campaign-code-label" id="homepage-nsy2627-code-label">', section)
        self.assertIn('<code>NSY2627</code>', section)
        self.assertEqual(section.count('class="campaign-primary-cta"'), 1)
        self.assertIn('class="campaign-secondary-links"', section)
        self.assertNotIn('class="btn campaign-cta"', section)

    def test_featured_campaign_css_is_scoped_and_responsive(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".campaign-featured .campaign-inner {\n  display: grid;", css)
        self.assertIn("grid-template-columns: minmax(0, 1.2fr) minmax(360px, .8fr)", css)
        self.assertIn(".campaign-featured .campaign-action {", css)
        self.assertIn(".campaign-featured .campaign-code-card {", css)
        self.assertIn(".campaign-featured .campaign-primary-cta {", css)
        self.assertIn(".campaign-featured .campaign-secondary-links a { min-height: 36px;", css)
        self.assertIn(".campaign-featured .campaign-inner { grid-template-columns: 1fr; gap: 24px; }", css)
        self.assertIn('styles.css?v=nsy2627-layout-20260911', (ROOT / "index.html").read_text(encoding="utf-8"))

    def test_rendered_layout_contract(self):
        result = subprocess.run(
            ["node", "tests/homepage-campaign.browser.cjs"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
