import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
HOMEPAGE = ROOT / "index.html"
PILLAR = ROOT / "tak12-on-thi-lop-6" / "index.html"
TIMELINE = ROOT / "lo-trinh-on-thi-vao-lop-6" / "index.html"
STRATEGY = ROOT / "kinh-nghiem-on-thi-vao-lop-6" / "index.html"
LLMS = ROOT / "llms.txt"
KEYWORD_MAP = ROOT / "docs" / "keyword-map.md"
OFFICIAL_LUYEN_DE_SOURCE = (
    "https://tak12.com/news/n/2499/"
    "tang-khoa-luyen-de-vao-6-cho-hoc-vien-tak12"
)
SCHOOL_GUIDES = {
    "kinh-nghiem-thi-vao-lop-6-nguyen-tat-thanh": (
        "Nguyễn Tất Thành",
        "https://tak12.com/info/vao-6-ntt?ref=njg2odn",
    ),
    "kinh-nghiem-thi-vao-lop-6-cau-giay": (
        "Cầu Giấy",
        "https://tak12.com/info/vao-6-cau-giay?ref=njg2odn",
    ),
    "kinh-nghiem-thi-vao-lop-6-thanh-xuan": (
        "Thanh Xuân",
        "https://tak12.com/info/vao-6-thanh-xuan?ref=njg2odn",
    ),
}

ALL_TAK12_SCHOOL_PROGRAMS = (
    "Nguyễn Tất Thành",
    "Lương Thế Vinh",
    "Cầu Giấy",
    "THCS Ngoại ngữ",
    "Thanh Xuân",
    "Nam Từ Liêm",
    "Archimedes",
    "Ngôi Sao Hà Nội",
    "Đoàn Thị Điểm",
    "Marie Curie",
    "Lê Lợi",
    "Năng khiếu ĐHSP",
)


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


class RootAffiliateCtaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._current = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and urlparse(attrs.get("href", "")).path == "/":
            self._current = {"attrs": attrs, "text": []}

    def handle_data(self, data):
        if self._current is not None:
            self._current["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._current is not None:
            self._current["label"] = " ".join("".join(self._current["text"]).split())
            self.links.append(self._current)
            self._current = None


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
    def test_current_lop6_luyen_de_offer_has_coordinated_source_safe_coverage(self):
        homepage = read(HOMEPAGE)
        pillar = read(PILLAR)
        llms = read(LLMS)
        keyword_map = read(KEYWORD_MAP)

        for name, document in {
            "homepage": homepage,
            "pillar": pillar,
            "llms": llms,
        }.items():
            with self.subTest(surface=name):
                self.assertIn("18 buổi", document)
                self.assertIn("09/11/2026", document)
                self.assertIn("gói ôn thi vào lớp 6", document.lower())
                self.assertIn("còn hạn PRO", document)
                self.assertIn("không áp dụng", document.lower())
                self.assertIn("Thi thử vào 6", document)
                self.assertIn(OFFICIAL_LUYEN_DE_SOURCE, document)

        self.assertIn('id="lop6-luyen-de-2027"', homepage)
        self.assertIn('data-cta="homepage_lop6_luyen_de_pricing"', homepage)
        self.assertIn('data-intent="exam_grade_6"', homepage)
        self.assertIn('rel="sponsored noopener"', homepage)
        self.assertIn('href="/tak12-on-thi-lop-6/#luyen-de-3-mon-2027"', homepage)
        self.assertIn('id="luyen-de-3-mon-2027"', pillar)
        self.assertIn("khóa luyện đề vào 6", keyword_map.lower())
        self.assertIn("tak12-on-thi-lop-6", keyword_map)

    def test_pillar_title_targets_the_current_2027_exam_cycle(self):
        title_match = re.search(r"<title>(.*?)</title>", read(PILLAR), re.DOTALL)

        self.assertIsNotNone(title_match)
        assert title_match is not None
        title = title_match.group(1)
        self.assertIn("2027", title)
        self.assertNotIn("2026", title)

    def test_generic_provider_links_do_not_promise_to_start_a_free_trial(self):
        parser = RootAffiliateCtaParser()
        parser.feed(read(PILLAR))

        self.assertGreaterEqual(len(parser.links), 5)
        for link in parser.links:
            with self.subTest(cta=link["attrs"].get("data-cta")):
                self.assertEqual("visit-provider", link["attrs"].get("data-intent"))
                self.assertIn("tak12", link["label"].lower())

    def test_pillar_links_to_the_two_supporting_pages(self):
        html = read(PILLAR)
        self.assertIn("../lo-trinh-on-thi-vao-lop-6/", html)
        self.assertIn("../kinh-nghiem-on-thi-vao-lop-6/", html)

    def test_pillar_lists_all_current_tak12_school_programs_and_links_to_priority_guides(self):
        html = read(PILLAR)
        for school in ALL_TAK12_SCHOOL_PROGRAMS:
            with self.subTest(school=school):
                self.assertIn(school, html)
        for slug in SCHOOL_GUIDES:
            with self.subTest(slug=slug):
                self.assertIn(f"../{slug}/", html)

    def test_priority_school_guides_are_indexable_specific_and_route_to_matching_programs(self):
        for slug, (school, product_url) in SCHOOL_GUIDES.items():
            page = ROOT / slug / "index.html"
            with self.subTest(school=school):
                self.assertTrue(page.is_file())
                html = read(page)
                self.assertIn('<meta name="robots" content="index, follow">', html)
                self.assertIn(
                    f'<link rel="canonical" href="https://tak-12.com/{slug}/">',
                    html,
                )
                self.assertIn(f"Kinh Nghiệm Thi Vào Lớp 6 {school}", html)
                self.assertIn(product_url, html)
                self.assertIn("thông báo tuyển sinh chính thức", html.lower())
                self.assertIn("../tak12-on-thi-lop-6/", html)
                self.assertIn('rel="sponsored noopener"', html)

    def test_priority_school_guides_have_visible_faq_schema_parity(self):
        for slug in SCHOOL_GUIDES:
            page = ROOT / slug / "index.html"
            with self.subTest(slug=slug):
                visible, schema = faq_pairs(page)
                self.assertGreaterEqual(len(visible), 3)
                self.assertEqual(visible, schema)

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
