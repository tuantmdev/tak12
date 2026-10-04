import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOMEPAGE = ROOT / "index.html"


class HomepageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.h1 = ""
        self.hero_text = []
        self.courses_text = []
        self.course_ctas = {}
        self.routes = {}
        self._stack = []
        self._course_cta = None
        self._capture = None
        self._hero_depth = 0
        self._courses_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self._stack.append(tag)
        if "hero" in str(attrs.get("class", "")).split():
            self._hero_depth += 1
        if tag == "section" and attrs.get("id") == "courses-section":
            self._courses_depth += 1
        if tag == "meta" and attrs.get("name") == "description":
            self.description = attrs.get("content", "")
        if tag == "a" and attrs.get("data-homepage-route"):
            self.routes[attrs["data-homepage-route"]] = attrs
        if tag == "a" and self._courses_depth and attrs.get("data-cta"):
            self._course_cta = {"attrs": attrs, "text": []}
        if tag == "title":
            self._capture = "title"
        elif tag == "h1":
            self._capture = "h1"

    def handle_data(self, data):
        if self._capture == "title":
            self.title += data
        elif self._capture == "h1":
            self.h1 += data
        if self._hero_depth:
            self.hero_text.append(data)
        if self._courses_depth:
            self.courses_text.append(data)
        if self._course_cta is not None:
            self._course_cta["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._course_cta is not None:
            attrs = self._course_cta["attrs"]
            self.course_ctas[attrs["data-cta"]] = {
                "attrs": attrs,
                "label": " ".join("".join(self._course_cta["text"]).split()),
            }
            self._course_cta = None
        if tag == "section" and self._hero_depth:
            self._hero_depth -= 1
        if tag == "section" and self._courses_depth:
            self._courses_depth -= 1
        if tag == self._capture:
            self._capture = None
        if self._stack:
            self._stack.pop()


class HomepageQualifiedIntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = HomepageParser()
        cls.parser.feed(HOMEPAGE.read_text(encoding="utf-8"))

    def test_search_metadata_and_h1_present_independent_review_intent(self):
        for value in (self.parser.title, self.parser.description, self.parser.h1):
            normalized = " ".join(value.lower().split())
            with self.subTest(value=value):
                self.assertIn("tak12", normalized)
                self.assertTrue(
                    "đánh giá" in normalized or "review" in normalized,
                    "Search metadata and H1 must set independent review/selection intent",
                )

    def test_homepage_search_metadata_uses_independent_review_intent_without_unverified_access_claims(self):
        title = " ".join(self.parser.title.lower().split())
        description = " ".join(self.parser.description.lower().split())

        self.assertIn("tak12", title)
        self.assertIn("đánh giá", title)
        self.assertIn("độc lập", description)
        for claim in ("học thử miễn phí", "tài khoản free", "free/pro"):
            with self.subTest(claim=claim):
                self.assertNotIn(claim, title)
                self.assertNotIn(claim, description)

    def test_hero_leads_with_parent_learning_hook_without_unverified_access_claims(self):
        hero = " ".join("".join(self.parser.hero_text).lower().split())
        self.assertIn("con đang cần một lộ trình học phù hợp", hero)
        self.assertNotIn("không phải website chính thức", hero)
        for claim in ("dùng thử miễn phí", "tài khoản free", "free/pro"):
            with self.subTest(claim=claim):
                self.assertNotIn(claim, hero)

    def test_featured_courses_use_selection_guidance_without_unsupported_popularity_claims(self):
        courses = " ".join("".join(self.parser.courses_text).lower().split())
        self.assertIn("chọn theo mục tiêu học tập", courses)
        for unsupported_claim in ("lựa chọn nhiều nhất", "bán chạy nhất"):
            with self.subTest(unsupported_claim=unsupported_claim):
                self.assertNotIn(unsupported_claim, courses)

    def test_featured_course_ctas_describe_their_pricing_destinations(self):
        expected = {
            "course_lop6": ("/info/bang-gia-vao-6", "exam_grade_6"),
            "course_cambridge": ("/info/bang-gia-chung-chi", "certification"),
            "course_toan_anh": ("/info/bang-gia-hoc-tot", "school_support"),
        }
        self.assertTrue(set(expected).issubset(self.parser.course_ctas))
        for cta_id, (destination_path, intent) in expected.items():
            with self.subTest(cta_id=cta_id):
                cta = self.parser.course_ctas[cta_id]
                self.assertIn(destination_path, cta["attrs"]["href"])
                self.assertEqual(intent, cta["attrs"].get("data-intent"))
                self.assertEqual("Xem Gói & Học Phí →", cta["label"])

    def test_homepage_routes_provider_review_and_selection_to_distinct_semantic_destinations(self):
        expected = {
            "provider-exploration": (
                "https://tak12.com/?ref=njg2odn",
                "visit-provider",
                "Truy cập TAK12 để xem chương trình",
            ),
            "independent-review": ("/tak12-co-tot-khong/", "read-independent-review", "Đọc review"),
            "free-vs-paid": ("/tak12-ma-giam-gia/", "compare-free-vs-paid", "So sánh FREE và trả phí"),
        }
        self.assertEqual(set(expected), set(self.parser.routes))
        for route, (href, intent, label) in expected.items():
            with self.subTest(route=route):
                attrs = self.parser.routes[route]
                self.assertEqual(href, attrs.get("href"))
                self.assertEqual(intent, attrs.get("data-intent"))
                self.assertEqual(label, attrs.get("aria-label"))
                if route == "provider-exploration":
                    self.assertEqual("homepage-hero-provider-exploration", attrs.get("data-cta"))
                    self.assertIn("ref=njg2odn", attrs["href"])
                    self.assertEqual(
                        {"sponsored", "noopener"},
                        set(str(attrs.get("rel", "")).split()),
                    )
                else:
                    self.assertEqual("noopener", attrs.get("rel"))


if __name__ == "__main__":
    unittest.main()
