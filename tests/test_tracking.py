import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML_PAGES = sorted(ROOT.rglob("index.html"))


class SitewideTrackingTests(unittest.TestCase):
    def test_every_page_loads_shared_analytics_before_interactions(self):
        self.assertEqual(9, len(HTML_PAGES), "Expected homepage plus eight SEO landing pages")

        for page in HTML_PAGES:
            html = page.read_text(encoding="utf-8")
            expected_prefix = "" if page.parent == ROOT else "../"
            analytics_tag = f'<script src="{expected_prefix}analytics.js"></script>'
            interactions_tag = f'<script src="{expected_prefix}script.js"></script>'
            analytics_position = html.find(analytics_tag)
            interactions_position = html.find(interactions_tag)

            with self.subTest(page=page.relative_to(ROOT)):
                self.assertGreaterEqual(analytics_position, 0, "Shared analytics.js path is missing or incorrect")
                self.assertGreaterEqual(interactions_position, 0, "Shared script.js path is missing or incorrect")
                self.assertLess(analytics_position, interactions_position)

    def test_posthog_is_initialized_exactly_once_in_shared_analytics_file(self):
        analytics = ROOT / "analytics.js"
        self.assertTrue(analytics.exists(), "analytics.js does not exist")

        tracked_sources = HTML_PAGES + sorted(ROOT.glob("*.js"))
        initializers = [
            source.relative_to(ROOT)
            for source in tracked_sources
            if "posthog.init" in source.read_text(encoding="utf-8")
        ]
        self.assertEqual([Path("analytics.js")], initializers)
        self.assertEqual(1, analytics.read_text(encoding="utf-8").count("posthog.init"))

    def test_campaign_ctas_declare_non_default_intent(self):
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertRegex(homepage, r'data-cta="campaign_banner"[^>]+data-intent="campaign_achieve_matific"')
        self.assertRegex(homepage, r'data-cta="campaign_banner_stars"[^>]+data-intent="campaign_summer_challenge"')
        self.assertIn("this.getAttribute('data-intent') || getAffiliateIntent", (ROOT / "script.js").read_text(encoding="utf-8"))

    def test_affiliate_click_event_has_attribution_properties(self):
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertIn("affiliate_cta_click", script)
        for prop in ("source_page", "cta_id", "position", "intent", "destination_url"):
            with self.subTest(property=prop):
                self.assertRegex(script, rf"\b{prop}\s*:")


if __name__ == "__main__":
    unittest.main()
