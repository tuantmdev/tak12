import json
import re
import unittest
from html import unescape
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "tak12-cambridge-ket-pet-flyers" / "index.html"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.cta_ids = []
        self.affiliate_links = []
        self.json_ld = []
        self._in_json_ld = False
        self._json_buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        href = attrs.get("href") or ""
        if tag == "a" and "ref=njg2odn" in href:
            self.affiliate_links.append(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if attrs.get("data-cta"):
            self.cta_ids.append(attrs["data-cta"])
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_buffer = []

    def handle_data(self, data):
        if self._in_json_ld:
            self._json_buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_json_ld:
            self.json_ld.append(json.loads("".join(self._json_buffer)))
            self._in_json_ld = False


class CambridgeSeoCroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.parser = PageParser()
        cls.parser.feed(cls.html)

    def test_search_snippet_targets_commercial_cambridge_queries(self):
        title_match = re.search(r"<title>(.*?)</title>", self.html, re.S)
        description_match = re.search(r'<meta name="description" content="([^"]+)">', self.html)
        self.assertIsNotNone(title_match)
        self.assertIsNotNone(description_match)
        title = title_match[1].strip() if title_match else ""
        description = description_match[1] if description_match else ""
        for term in ("TAK12", "Flyers", "KET", "PET"):
            self.assertIn(term, title)
        self.assertLessEqual(len(title), 60)
        self.assertIn("TOEFL Primary", description)
        self.assertIn("dùng thử", description.lower())
        self.assertLessEqual(len(description), 160)

    def test_social_metadata_matches_updated_search_positioning(self):
        def content(pattern):
            match = re.search(pattern, self.html, re.S)
            self.assertIsNotNone(match)
            return match[1] if match else ""

        title = content(r"<title>(.*?)</title>").strip()
        description = content(r'<meta name="description" content="([^"]+)">')
        twitter_title = content(r'<meta name="twitter:title" content="([^"]+)">')
        twitter_description = content(r'<meta name="twitter:description" content="([^"]+)">')
        self.assertEqual(unescape(twitter_title), unescape(title))
        self.assertEqual(unescape(twitter_description), unescape(description))
        self.assertIn("TOEFL Primary", twitter_title)
        self.assertIn("TOEFL Primary", twitter_description)

    def test_each_high_intent_certificate_has_a_dedicated_section(self):
        for section_id in ("flyers", "ket", "pet", "toefl-primary"):
            with self.subTest(section=section_id):
                self.assertIn(section_id, self.parser.ids)

    def test_page_explains_free_vs_paid_before_purchase(self):
        self.assertIn('id="free-vs-pro"', self.html)
        for phrase in ("Tài khoản FREE", "Khóa trả phí", "Nên chọn"):
            self.assertIn(phrase, self.html)

    def test_conversion_ctas_are_unique_and_cover_the_funnel(self):
        self.assertEqual(len(self.parser.cta_ids), len(set(self.parser.cta_ids)))
        for cta_id in (
            "cambridge_hero_trial",
            "cambridge_flyers_pricing",
            "cambridge_ket_pricing",
            "cambridge_pet_pricing",
            "cambridge_bottom_trial",
        ):
            self.assertIn(cta_id, self.parser.cta_ids)

    def test_affiliate_disclosure_and_internal_links_are_present(self):
        self.assertIn("tiếp thị liên kết", self.html.lower())
        self.assertIn('../tak12-co-tot-khong/', self.html)
        self.assertIn('../tak12-ma-giam-gia/', self.html)
        self.assertIn('../tak12-luyen-thi-ielts/', self.html)

    def test_affiliate_disclosure_precedes_first_affiliate_link(self):
        disclosure_position = self.html.lower().find("tiếp thị liên kết")
        affiliate_link = re.search(r'<a\b[^>]*href="[^"]*ref=njg2odn', self.html, re.I)
        self.assertGreaterEqual(disclosure_position, 0)
        self.assertIsNotNone(affiliate_link)
        self.assertLess(disclosure_position, affiliate_link.start() if affiliate_link else -1)

    def test_all_affiliate_links_are_safely_marked_as_sponsored(self):
        self.assertTrue(self.parser.affiliate_links)
        for link in self.parser.affiliate_links:
            with self.subTest(href=link["href"]):
                rel_tokens = set(link.get("rel", "").split())
                self.assertIn("noopener", rel_tokens)
                self.assertIn("sponsored", rel_tokens)

    def test_structured_data_matches_visible_content(self):
        schema_types = {schema.get("@type") for schema in self.parser.json_ld}
        self.assertTrue({"BreadcrumbList", "Course", "FAQPage"}.issubset(schema_types))
        faq_schema = next(schema for schema in self.parser.json_ld if schema.get("@type") == "FAQPage")

        def normalize(value):
            without_tags = re.sub(r"<[^>]+>", " ", value)
            return " ".join(unescape(without_tags).split())

        visible_faqs = {
            normalize(question): normalize(answer)
            for question, answer in re.findall(
                r'<div class="faq-item">.*?<span class="q-text">(.*?)</span>.*?<div class="a-inner">(.*?)</div>',
                self.html,
                re.S,
            )
        }
        schema_faqs = {
            normalize(item["name"]): normalize(item["acceptedAnswer"]["text"])
            for item in faq_schema["mainEntity"]
        }
        self.assertEqual(schema_faqs, visible_faqs)


if __name__ == "__main__":
    unittest.main()
