import json
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILLAR = ROOT / "tak12-on-thi-lop-10-ha-noi" / "index.html"
TIMELINE = ROOT / "lo-trinh-on-thi-vao-lop-10-ha-noi" / "index.html"


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


class Lop10ContentClusterTests(unittest.TestCase):
    def test_pillar_links_to_the_lop10_planning_page(self):
        self.assertIn("../lo-trinh-on-thi-vao-lop-10-ha-noi/", read(PILLAR))

    def test_planning_page_is_indexable_links_to_the_pillar_and_has_qualified_cta(self):
        html = read(TIMELINE)
        self.assertIn('<meta name="robots" content="index, follow">', html)
        self.assertIn(
            '<link rel="canonical" href="https://tak-12.com/lo-trinh-on-thi-vao-lop-10-ha-noi/">',
            html,
        )
        self.assertIn("../tak12-on-thi-lop-10-ha-noi/", html)
        self.assertIn('data-cta="lop10_timeline_course"', html)
        self.assertIn('data-intent="exam_grade_10"', html)
        self.assertIn('rel="sponsored noopener"', html)

    def test_planning_page_serves_2026_2027_planning_intent_without_unsupported_school_claims(self):
        html = read(TIMELINE).lower()
        self.assertIn("năm học 2026–2027", html)
        self.assertIn("thông báo tuyển sinh chính thức", html)
        self.assertNotIn("đảm bảo đỗ", html)
        self.assertNotIn("tỷ lệ đỗ", html)

    def test_visible_faq_exactly_matches_faq_schema(self):
        visible, schema = faq_pairs(TIMELINE)
        self.assertGreaterEqual(len(visible), 3)
        self.assertEqual(visible, schema)


if __name__ == "__main__":
    unittest.main()
