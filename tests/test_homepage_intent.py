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
        self.routes = {}
        self._stack = []
        self._capture = None
        self._hero_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self._stack.append(tag)
        if "hero" in str(attrs.get("class", "")).split():
            self._hero_depth += 1
        if tag == "meta" and attrs.get("name") == "description":
            self.description = attrs.get("content", "")
        if tag == "a" and attrs.get("data-homepage-route"):
            self.routes[attrs["data-homepage-route"]] = attrs
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

    def handle_endtag(self, tag):
        if tag == "section" and self._hero_depth:
            self._hero_depth -= 1
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

    def test_hero_says_site_is_independent_and_not_the_official_tak12_site(self):
        hero = " ".join("".join(self.parser.hero_text).lower().split())
        self.assertIn("trang thông tin độc lập", hero)
        self.assertIn("không phải website chính thức", hero)

    def test_homepage_routes_login_review_and_free_vs_paid_to_distinct_semantic_destinations(self):
        expected = {
            "official-login": ("https://tak12.com/", None, "Đăng nhập"),
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
                if route == "official-login":
                    self.assertNotIn("ref=", attrs["href"])
                    self.assertNotIn("sponsored", str(attrs.get("rel", "")).split())
                else:
                    self.assertEqual("noopener", attrs.get("rel"))


if __name__ == "__main__":
    unittest.main()
