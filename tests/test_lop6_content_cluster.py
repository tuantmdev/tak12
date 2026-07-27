import json
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILLAR = ROOT / "tak12-on-thi-lop-6" / "index.html"
TIMELINE = ROOT / "lo-trinh-on-thi-vao-lop-6" / "index.html"
STRATEGY = ROOT / "kinh-nghiem-on-thi-vao-lop-6" / "index.html"


class VisibleFaqParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._stack = []
        self._json_buffer = []
        self._in_json_ld = False
        self.questions = []
        self.answers = []
        self.schemas = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self._stack.append((tag, attrs, []))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_buffer = []

    def handle_data(self, data):
        if self._in_json_ld:
            self._json_buffer.append(data)
        for _, _, text in self._stack:
            text.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_json_ld:
            self.schemas.append(json.loads("".join(self._json_buffer)))
            self._in_json_ld = False
        for index in range(len(self._stack) - 1, -1, -1):
            current_tag, attrs, text = self._stack[index]
            if current_tag == tag:
                normalized = " ".join("".join(text).split())
                classes = attrs.get("class", "").split()
                if "q-text" in classes:
                    self.questions.append(normalized)
                if "a-inner" in classes:
                    self.answers.append(normalized)
                del self._stack[index:]
                break


def read(page):
    return page.read_text(encoding="utf-8")


def faq_pairs(page):
    parser = VisibleFaqParser()
    parser.feed(read(page))
    schema = next(item for item in parser.schemas if item.get("@type") == "FAQPage")
    return (
        list(zip(parser.questions, parser.answers)),
        [(item["name"], item["acceptedAnswer"]["text"]) for item in schema["mainEntity"]],
    )


class Lop6ContentClusterTests(unittest.TestCase):
    def test_pillar_links_to_the_two_supporting_pages(self):
        html = read(PILLAR)
        self.assertIn("../lo-trinh-on-thi-vao-lop-6/", html)
        self.assertIn("../kinh-nghiem-on-thi-vao-lop-6/", html)

    def test_supporting_pages_are_indexable_and_link_back_to_the_pillar(self):
        for page in (TIMELINE, STRATEGY):
            with self.subTest(page=page):
                html = read(page)
                self.assertIn('<meta name="robots" content="index, follow">', html)
                self.assertIn('<link rel="canonical" href="https://tak-12.com/', html)
                self.assertIn("../tak12-on-thi-lop-6/", html)
                self.assertIn("data-cta=", html)
                self.assertIn('rel="sponsored noopener"', html)

    def test_timeline_serves_the_2027_exam_planning_intent_without_claiming_search_demand(self):
        html = read(TIMELINE).lower()
        self.assertIn("hè 2026", html)
        self.assertIn("kỳ thi năm 2027", html)
        self.assertNotIn("từ khóa sinh năm 2016", html)

    def test_visible_faq_exactly_matches_faq_schema_on_the_supporting_pages(self):
        for page in (TIMELINE, STRATEGY):
            with self.subTest(page=page):
                visible, schema = faq_pairs(page)
                self.assertGreaterEqual(len(visible), 2)
                self.assertEqual(visible, schema)


if __name__ == "__main__":
    unittest.main()
