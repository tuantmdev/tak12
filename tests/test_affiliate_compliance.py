import json
import re
import subprocess
import unittest
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
HTML_PAGES = sorted(ROOT.rglob("index.html"))


class ComplianceParser(HTMLParser):
    HIDDEN_CLASSES = {"hidden", "d-none", "invisible"}
    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__()
        self.affiliate_links = []
        self.disclosure_positions = []
        self.json_ld = []
        self.visible_faq_questions = []
        self.visible_faq_answers = []
        self.prose_h2_count = 0
        self.direct_prose_h2_count = 0
        self._in_json_ld = False
        self._json_buffer = []
        self._position = 0
        self._stack = []

    @staticmethod
    def _is_affiliate_url(href):
        destination = urlparse(href)
        return (
            destination.scheme in {"http", "https"}
            and "ref" in parse_qs(destination.query)
        )

    @classmethod
    def _element_is_hidden(cls, tag, attrs):
        classes = set((attrs.get("class") or "").lower().split())
        styles = {}
        for declaration in (attrs.get("style") or "").lower().split(";"):
            if ":" in declaration:
                name, value = declaration.split(":", 1)
                styles[name.strip()] = value.replace("!important", "").strip()
        return (
            tag in {"script", "style", "template"}
            or "hidden" in attrs
            or (attrs.get("aria-hidden") or "").strip().lower() == "true"
            or bool(classes & cls.HIDDEN_CLASSES)
            or styles.get("display") == "none"
            or styles.get("visibility") == "hidden"
        )

    @staticmethod
    def _is_clear_disclosure(text):
        normalized = " ".join(text.lower().split())
        return bool(normalized) and any(
            phrase in normalized
            for phrase in ("tiếp thị liên kết", "hoa hồng", "affiliate", "commission")
        )

    def handle_starttag(self, tag, attrs):
        self._position += 1
        attrs = dict(attrs)
        parent_hidden = self._stack[-1]["hidden"] if self._stack else False
        self_hidden = self._element_is_hidden(tag, attrs)
        hidden = parent_hidden or self_hidden
        is_affiliate = tag == "a" and self._is_affiliate_url(attrs.get("href", ""))
        in_body = tag == "body" or any(node["tag"] == "body" for node in self._stack)
        parent = self._stack[-1] if self._stack else None
        node = {
            "tag": tag,
            "attrs": attrs,
            "hidden": hidden,
            "self_hidden": self_hidden,
            "in_body": in_body,
            "is_affiliate": is_affiliate,
            "position": self._position,
            "disclosure_position": None,
            "text": [],
        }
        if tag not in self.VOID_ELEMENTS:
            self._stack.append(node)

        if tag == "h2":
            in_prose = any(
                "lp-prose" in item["attrs"].get("class", "").split()
                for item in self._stack[:-1]
            )
            if in_prose:
                self.prose_h2_count += 1
            if parent and "lp-prose" in parent["attrs"].get("class", "").split():
                self.direct_prose_h2_count += 1

        if is_affiliate:
            self.affiliate_links.append({"attrs": attrs, "position": self._position, "text": node["text"]})

        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_buffer = []

    def handle_data(self, data):
        self._position += 1
        if not self._stack or not self._stack[-1]["hidden"]:
            for node in self._stack:
                node["text"].append(data)
            for node in self._stack:
                if (
                    node["disclosure_position"] is None
                    and "data-affiliate-disclosure" in node["attrs"]
                    and node["in_body"]
                    and self._is_clear_disclosure("".join(node["text"]))
                ):
                    node["disclosure_position"] = self._position
        else:
            for index, node in enumerate(self._stack):
                if node["is_affiliate"] and not any(
                    descendant["self_hidden"] for descendant in self._stack[index + 1:]
                ):
                    node["text"].append(data)
        if self._in_json_ld:
            self._json_buffer.append(data)

    def handle_endtag(self, tag):
        self._position += 1
        if tag == "script" and self._in_json_ld:
            self.json_ld.append(json.loads("".join(self._json_buffer)))
            self._in_json_ld = False
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index]["tag"] == tag:
                node = self._stack[index]
                classes = node["attrs"].get("class", "").split()
                text = " ".join("".join(node["text"]).split())
                if (
                    "data-affiliate-disclosure" in node["attrs"]
                    and node["in_body"]
                    and not node["hidden"]
                    and node["disclosure_position"] is not None
                ):
                    self.disclosure_positions.append(node["disclosure_position"])
                if "q-text" in classes and not node["hidden"]:
                    self.visible_faq_questions.append(text)
                if "a-inner" in classes and not node["hidden"]:
                    self.visible_faq_answers.append(text)
                del self._stack[index:]
                break


class AffiliateComplianceTests(unittest.TestCase):
    def parse_page(self, page):
        parser = ComplianceParser()
        parser.feed(page.read_text(encoding="utf-8"))
        return parser

    def test_visible_disclosure_precedes_first_affiliate_link_on_every_page(self):
        self.assertEqual(9, len(HTML_PAGES))
        for page in HTML_PAGES:
            parser = self.parse_page(page)
            with self.subTest(page=page.relative_to(ROOT)):
                self.assertTrue(parser.affiliate_links, "Expected at least one ref-tagged affiliate link")
                self.assertTrue(
                    any(
                        position < parser.affiliate_links[0]["position"]
                        for position in parser.disclosure_positions
                    ),
                    "Expected a visible body disclosure before the first affiliate link",
                )

    def test_every_affiliate_link_is_sponsored_and_blank_links_are_noopener(self):
        total_links = 0
        for page in HTML_PAGES:
            parser = self.parse_page(page)
            total_links += len(parser.affiliate_links)
            for link in parser.affiliate_links:
                attrs = link["attrs"]
                rel_tokens = set(attrs.get("rel", "").lower().split())
                with self.subTest(page=page.relative_to(ROOT), href=attrs.get("href")):
                    self.assertIn("sponsored", rel_tokens)
                    if attrs.get("target", "").lower() == "_blank":
                        self.assertIn("noopener", rel_tokens)
        self.assertEqual(66, total_links, "Affiliate-link fixture changed; review all new links")

    def test_every_affiliate_link_has_unique_cta_id_and_explicit_semantics(self):
        allowed_intents = {
            ("tak12.com", "/"): {"free_account", "start-free-trial", "test-learning-fit", "visit-provider"},
            ("tak12.com", "/info/bang-gia"): {"all_courses", "verify-current-price-and-access"},
            ("tak12.com", "/info/bang-gia-chung-chi"): {
                "certification", "certification_flyers", "certification_ket",
                "certification_pet", "certification_toefl_primary",
            },
            ("tak12.com", "/info/bang-gia-hoc-tot"): {"school_support"},
            ("tak12.com", "/info/bang-gia-vao-6"): {"exam_grade_6"},
            ("tak12.com", "/info/bang-gia-vao-10"): {"exam_grade_10"},
            ("tak12.com", "/info/bang-gia-vao-dh"): {"exam_university"},
            ("tak12.com", "/news/n/2454/thu-thach-45-ngay-thi-dua-he-hoc-chat-nhan-qua-that"): {
                "campaign_summer_challenge"
            },
            ("contuhoc.com", "/he-ruc-ro-hoc-het-co-uu-dai-den-30-achieve3000-matific"): {
                "campaign_achieve_matific"
            },
        }
        for page in HTML_PAGES:
            parser = self.parse_page(page)
            cta_ids = [link["attrs"].get("data-cta") for link in parser.affiliate_links]
            with self.subTest(page=page.relative_to(ROOT), contract="cta IDs"):
                self.assertTrue(all(cta_ids), "Every affiliate link must have a stable CTA ID")
                self.assertEqual(len(cta_ids), len(set(cta_ids)), "CTA IDs must be unique per page")

            for link in parser.affiliate_links:
                attrs = link["attrs"]
                destination = urlparse(attrs["href"])
                intent = attrs.get("data-intent")
                label = " ".join("".join(link["text"]).split()).lower()
                destination_key = ((destination.hostname or "").lower().removeprefix("www."), destination.path)
                with self.subTest(page=page.relative_to(ROOT), cta=attrs.get("data-cta")):
                    self.assertIn(destination_key, allowed_intents, "Unknown destination needs an explicit test rule")
                    self.assertIn(intent, allowed_intents[destination_key])
                    if destination_key[0] == "contuhoc.com":
                        self.assertEqual("campaign_achieve_matific", intent)
                        self.assertIn("ưu đãi", label, "Contuhoc campaign CTA must explicitly describe the offer")
                    elif intent == "visit-provider":
                        self.assertTrue("tak12.com" in label or "truy cập" in label)
                    elif destination.path == "/":
                        self.assertTrue(
                            any(term in label for term in ("free", "miễn phí", "dùng thử", "tài khoản")),
                            "Account destination label must communicate free/trial/account intent",
                        )
                    elif destination.path.startswith("/info/bang-gia"):
                        self.assertTrue(
                            any(term in label for term in ("đăng ký", "giá", "học phí", "khóa", "dùng thử")),
                            "Pricing destination label must communicate price/course intent",
                        )
                    else:
                        self.assertIn("tham gia", label)

    def test_hidden_or_empty_disclosures_do_not_satisfy_opening_position(self):
        parser = ComplianceParser()
        parser.feed("""
        <body>
          <div hidden><p data-affiliate-disclosure>Tiếp thị liên kết: nhận hoa hồng.</p></div>
          <div aria-hidden="true"><p data-affiliate-disclosure>Tiếp thị liên kết: nhận hoa hồng.</p></div>
          <div class="hidden"><p data-affiliate-disclosure>Tiếp thị liên kết: nhận hoa hồng.</p></div>
          <div style="display: none"><p data-affiliate-disclosure>Tiếp thị liên kết: nhận hoa hồng.</p></div>
          <p style="visibility:hidden" data-affiliate-disclosure>Tiếp thị liên kết: nhận hoa hồng.</p>
          <p data-affiliate-disclosure>   </p>
          <p data-affiliate-disclosure>Thông báo chung không nói về khoản bồi hoàn.</p>
          <p data-affiliate-disclosure>Tiếp thị liên kết: chúng tôi có thể nhận hoa hồng.</p>
          <a href="https://tak12.com/?ref=test">Dùng thử miễn phí</a>
        </body>
        """)
        self.assertEqual(1, len(parser.disclosure_positions))
        self.assertLess(parser.disclosure_positions[0], parser.affiliate_links[0]["position"])

    def test_disclosure_position_is_qualifying_visible_text_not_wrapper_start(self):
        parser = ComplianceParser()
        parser.feed("""
        <body>
          <div data-affiliate-disclosure>
            <a href="https://tak12.com/?ref=test">Dùng thử miễn phí</a>
            <p>Tiếp thị liên kết: chúng tôi có thể nhận hoa hồng.</p>
          </div>
        </body>
        """)
        self.assertEqual(1, len(parser.disclosure_positions))
        self.assertGreater(parser.disclosure_positions[0], parser.affiliate_links[0]["position"])

    def test_hidden_affiliate_descendant_text_cannot_supply_cta_semantics(self):
        parser = ComplianceParser()
        parser.feed("""
        <body>
          <a href="https://tak12.com/info/bang-gia?ref=test">
            Xem ngay<span hidden>Đăng ký khóa học và dùng thử</span>
          </a>
        </body>
        """)
        label = " ".join("".join(parser.affiliate_links[0]["text"]).split()).lower()
        self.assertEqual("xem ngay", label)
        self.assertFalse(any(term in label for term in ("đăng ký", "giá", "học phí", "khóa", "dùng thử")))

    def test_hidden_faq_nodes_and_hidden_descendant_text_are_not_visible_content(self):
        parser = ComplianceParser()
        parser.feed("""
        <body>
          <div class="hidden"><span class="q-text">Hidden question</span></div>
          <div aria-hidden="true"><span class="a-inner">Hidden answer</span></div>
          <span class="q-text">Visible question<span style="display:none"> secret</span></span>
          <span class="a-inner">Visible answer<span hidden> secret</span></span>
        </body>
        """)
        self.assertEqual(["Visible question"], parser.visible_faq_questions)
        self.assertEqual(["Visible answer"], parser.visible_faq_answers)

    def test_sitemap_json_ld_faq_and_heading_contracts_cover_all_pages(self):
        sitemap = ElementTree.parse(ROOT / "sitemap.xml")
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls: list[str] = [
            item.text
            for item in sitemap.findall("sm:url/sm:loc", namespace)
            if item.text is not None
        ]
        sitemap_pages = {
            ROOT / (urlparse(url).path.strip("/") or ".") / "index.html"
            for url in urls
        }
        sitemap_pages = {ROOT / "index.html" if path == ROOT / "index.html" else path for path in sitemap_pages}
        self.assertEqual(set(HTML_PAGES), sitemap_pages)

        def normalize(value):
            return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())

        styles = (ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".lp-prose > h2", styles)
        self.assertIn(".lp-prose > h2:first-child", styles)
        for page in HTML_PAGES:
            parser = self.parse_page(page)
            faq_schemas = [item for item in parser.json_ld if item.get("@type") == "FAQPage"]
            with self.subTest(page=page.relative_to(ROOT)):
                self.assertEqual(1, len(faq_schemas))
                self.assertEqual(parser.prose_h2_count, parser.direct_prose_h2_count)
                if page != ROOT / "index.html":
                    self.assertGreater(parser.prose_h2_count, 0)
                visible_faq = [
                    (normalize(question), normalize(answer))
                    for question, answer in zip(
                        parser.visible_faq_questions,
                        parser.visible_faq_answers,
                        strict=True,
                    )
                ]
                schema_faq = [
                    (
                        normalize(item["name"]),
                        normalize(item["acceptedAnswer"]["text"]),
                    )
                    for item in faq_schemas[0]["mainEntity"]
                ]
                self.assertEqual(visible_faq, schema_faq)

    def test_pages_do_not_publish_unsupported_partnership_or_testimonial_claims(self):
        forbidden_claims = (
            "đối tác liên kết chính thức",
            "nguyễn thị mai",
            "trần hoàng",
            "lê phương",
            "tăng 15 điểm toefl",
        )
        for page in HTML_PAGES:
            html = page.read_text(encoding="utf-8").lower()
            for claim in forbidden_claims:
                with self.subTest(page=page.relative_to(ROOT), claim=claim):
                    self.assertNotIn(claim, html)

    def test_home_navigation_labels_the_independent_evaluation_guide(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="#testimonials-section">Cách Đánh Giá</a>', html)
        self.assertNotIn('href="#testimonials-section">Đánh Giá</a>', html)

    def test_dynamic_quiz_cta_updates_intent_with_its_destination(self):
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        quiz_urls = {
            "https://tak12.com/info/bang-gia-chung-chi?ref=njg2odn": "certification",
            "https://tak12.com/info/bang-gia-vao-6?ref=njg2odn": "exam_grade_6",
            "https://tak12.com/info/bang-gia-vao-10?ref=njg2odn": "exam_grade_10",
            "https://tak12.com/info/bang-gia-vao-dh?ref=njg2odn": "exam_university",
            "https://tak12.com/info/bang-gia-hoc-tot?ref=njg2odn": "school_support",
        }
        export = "\n  globalThis.__getAffiliateIntent = getAffiliateIntent;\n"
        instrumented = script.rsplit("})();", 1)[0] + export + "})();"
        harness = f"""
const vm = require('vm');
const context = {{ document: {{ addEventListener: function () {{}} }} }};
context.globalThis = context;
vm.createContext(context);
vm.runInContext({json.dumps(instrumented)}, context);
const urls = {json.dumps(list(quiz_urls))};
process.stdout.write(JSON.stringify(urls.map(url => context.__getAffiliateIntent(url))));
"""
        result = subprocess.run(
            ["node", "-e", harness], capture_output=True, text=True, check=True
        )
        self.assertEqual(list(quiz_urls.values()), json.loads(result.stdout))
        self.assertIn("resLink.href = r.url", script)
        self.assertIn("resLink.setAttribute('data-intent', getAffiliateIntent(r.url))", script)


if __name__ == "__main__":
    unittest.main()
