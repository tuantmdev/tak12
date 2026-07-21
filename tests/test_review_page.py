import json
import re
import unittest
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "tak12-co-tot-khong" / "index.html"


class ReviewPageParser(HTMLParser):
    VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.ids = set()
        self.cta_ids = []
        self.ctas = {}
        self.affiliate_links = []
        self.affiliate_positions = []
        self.disclosure_positions = []
        self.prose_h2_ids = []
        self.direct_prose_h2_ids = []
        self.json_ld = []
        self._in_json_ld = False
        self._json_buffer = []
        self._position = 0
        self._stack = []

    def handle_starttag(self, tag, attrs):
        self._position += 1
        attrs = dict(attrs)
        href = attrs.get("href") or ""
        parent = self._stack[-1] if self._stack else None
        hidden = (parent["hidden"] if parent else False) or tag in {"script", "style", "template"}
        hidden = hidden or "hidden" in attrs or attrs.get("aria-hidden") == "true"
        node = {
            "tag": tag,
            "attrs": attrs,
            "start": self._position,
            "text": [],
            "hidden": hidden,
            "in_body": tag == "body" or any(ancestor["tag"] == "body" for ancestor in self._stack),
        }
        if tag not in self.VOID_ELEMENTS:
            self._stack.append(node)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "h2":
            in_prose = any(
                ancestor["tag"] == "article" and "lp-prose" in ancestor["attrs"].get("class", "").split()
                for ancestor in self._stack
            )
            if in_prose:
                self.prose_h2_ids.append(attrs.get("id"))
            if parent and parent["tag"] == "article" and "lp-prose" in parent["attrs"].get("class", "").split():
                self.direct_prose_h2_ids.append(attrs.get("id"))
        if attrs.get("data-cta"):
            cta_id = attrs["data-cta"]
            self.cta_ids.append(cta_id)
            self.ctas[cta_id] = {"attrs": attrs, "text": node["text"]}
        if tag == "a" and "ref=njg2odn" in href:
            self.affiliate_links.append(attrs)
            self.affiliate_positions.append(self._position)
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_buffer = []

    def handle_data(self, data):
        self._position += 1
        for node in self._stack:
            node["text"].append(data)
        if self._in_json_ld:
            self._json_buffer.append(data)

    def handle_endtag(self, tag):
        self._position += 1
        if tag == "script" and self._in_json_ld:
            self.json_ld.append(json.loads("".join(self._json_buffer)))
            self._in_json_ld = False
        if not self._stack:
            return
        node = self._stack.pop()
        if (
            node["tag"] not in {"body", "html"}
            and node["in_body"]
            and not node["hidden"]
            and "tiếp thị liên kết" in " ".join(node["text"]).lower()
        ):
            self.disclosure_positions.append(node["start"])


class ReviewSeoCroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.parser = ReviewPageParser()
        cls.parser.feed(cls.html)

    def test_search_snippet_targets_review_intent(self):
        title_match = re.search(r"<title>(.*?)</title>", self.html, re.S)
        description_match = re.search(r'<meta name="description" content="([^"]+)">', self.html)
        self.assertIsNotNone(title_match)
        self.assertIsNotNone(description_match)
        title = unescape(title_match[1].strip()) if title_match else ""
        description = unescape(description_match[1]) if description_match else ""
        for term in ("TAK12", "Có Tốt Không", "Review"):
            self.assertIn(term, title)
        self.assertLessEqual(len(title), 60)
        self.assertIn("phù hợp", description.lower())
        self.assertIn("không phù hợp", description.lower())
        self.assertIn("FREE", description)
        self.assertLessEqual(len(description), 160)

    def test_balanced_review_has_decision_sections(self):
        required_ids = (
            "ket-luan",
            "uu-diem",
            "nhuoc-diem",
            "phu-hop",
            "khong-phu-hop",
            "free-vs-paid",
        )
        for section_id in required_ids:
            with self.subTest(section=section_id):
                self.assertIn(section_id, self.parser.ids)
                self.assertIn(section_id, self.parser.direct_prose_h2_ids)
        self.assertEqual(self.parser.prose_h2_ids, self.parser.direct_prose_h2_ids)
        required_h2_order = [heading_id for heading_id in self.parser.direct_prose_h2_ids if heading_id in required_ids]
        self.assertEqual(required_h2_order, list(required_ids))

    def test_page_does_not_publish_unverified_testimonials(self):
        for unsupported_claim in ("Nguyễn Thị Mai", "Trần Hoàng", "Lê Phương", "tăng 15 điểm TOEFL"):
            with self.subTest(claim=unsupported_claim):
                self.assertNotIn(unsupported_claim, self.html)

    def test_conversion_ctas_are_unique_and_cover_decision_funnel(self):
        self.assertEqual(len(self.parser.cta_ids), len(set(self.parser.cta_ids)))
        expected = {
            "review_nav_trial": ("account", "start-free-trial", ("tài khoản", "free")),
            "review_hero_trial": ("account", "start-free-trial", ("miễn phí",)),
            "review_mid_trial": ("account", "test-learning-fit", ("dùng thử",)),
            "review_pricing": ("pricing", "verify-current-price-and-access", ("giá", "quyền truy cập")),
            "review_bottom_trial": ("account", "start-free-trial", ("tài khoản", "free")),
            "review_footer_provider": ("provider", "visit-provider", ("tak12.com",)),
        }
        self.assertEqual(set(self.parser.ctas), set(expected))
        for cta_id, (destination_type, intent, label_terms) in expected.items():
            with self.subTest(cta=cta_id):
                cta = self.parser.ctas[cta_id]
                destination = urlparse(cta["attrs"]["href"])
                destination_types = {"/": "provider" if intent == "visit-provider" else "account", "/info/bang-gia": "pricing"}
                label = " ".join("".join(cta["text"]).split()).lower()
                self.assertEqual(destination.netloc, "tak12.com")
                self.assertEqual(destination_types.get(destination.path), destination_type)
                self.assertEqual(cta["attrs"].get("data-intent"), intent)
                for term in label_terms:
                    self.assertIn(term, label)

    def test_all_affiliate_links_are_safely_marked_as_sponsored(self):
        self.assertTrue(self.parser.affiliate_links)
        for link in self.parser.affiliate_links:
            with self.subTest(href=link["href"]):
                rel_tokens = set(link.get("rel", "").split())
                self.assertIn("noopener", rel_tokens)
                self.assertIn("sponsored", rel_tokens)

    def test_structured_data_matches_visible_faq_content(self):
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
