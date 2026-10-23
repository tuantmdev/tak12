import json
import os
import re
import subprocess
import unittest
from html.parser import HTMLParser
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://tak12.com/news/n/2499/tang-khoa-luyen-de-vao-6-cho-hoc-vien-tak12"


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class OctoberLop6CampaignTests(unittest.TestCase):
    def test_october_offer_is_accurate_discoverable_and_expires_at_vietnam_midnight(self):
        offers = []
        ctas = []
        for path, section_id, prefix in [
            ("index.html", "homepage-october-lop6", "homepage"),
            ("tak12-on-thi-lop-6/index.html", "october-lop6", "lop6"),
        ]:
            html = (ROOT / path).read_text()
            match = re.search(r'<section\b[^>]*id="' + section_id + r'"[^>]*>.*?</section>', html, re.S)
            self.assertIsNotNone(match, f"Missing October offer section in {path}")
            section = match.group()
            tags = Tags(section).tags
            attrs = tags[0][1]
            self.assertIn("hidden", attrs, "No-JS visits must keep the offer hidden")
            self.assertIn("data-dated-offer", attrs)
            self.assertEqual("31/10/2026", attrs["data-end-date"])
            offers.append(attrs)
            for fact in ["08/10", "31/10/2026", "giờ Việt Nam", "Thi thử vào 6",
                         "Trọn bộ ôn thi vào 6", "lớp 3, 4, 5",
                         "Combo Luyện đề 3 môn 12 trường THCS CLC", "lớp 4, 5",
                         "thời hạn", "gói ôn luyện được kích hoạt"]:
                self.assertIn(fact, section)
            links = [a for t, a in tags if t == "a"]
            for suffix, url, intent in [
                ("pricing", "https://tak12.com/info/bang-gia-vao-6?ref=njg2odn", "exam_grade_6"),
                ("source", SOURCE + "?ref=njg2odn", "verify-offer-terms"),
            ]:
                link = next(a for a in links if a.get("data-cta") == f"{prefix}_october_lop6_{suffix}")
                self.assertEqual(url, link["href"])
                self.assertEqual("_blank", link["target"])
                self.assertEqual({"sponsored", "noopener"}, set(link["rel"].split()))
                self.assertEqual(intent, link["data-intent"])
                if prefix == "lop6":
                    self.assertIn("btn", link.get("class", "").split())
            ctas.extend(a["data-cta"] for a in links)
            if prefix == "homepage":
                self.assertTrue(any(a["href"] == "/tak12-on-thi-lop-6/#october-lop6" for a in links))
            for marker in ["08/10", "31/10/2026", "october-lop6"]:
                self.assertNotIn(marker, html.split("</head>")[0])
                self.assertNotIn(marker, (ROOT / "llms.txt").read_text())
                for schema in re.findall(
                    r'<script\b[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                    html,
                    re.S,
                ):
                    json.loads(schema)
                    self.assertNotIn(marker, schema)
            self.assertNotIn("affiliate-disclosure", section)
            self.assertNotIn("data-affiliate-disclosure", section)
            self.assertIn(f'data-cta="{prefix}_luyen_de_pricing"' if prefix == "lop6"
                          else 'data-cta="homepage_lop6_luyen_de_pricing"', html)
        self.assertEqual(len(ctas), len(set(ctas)))

        # Execute the shipped DOMContentLoaded wiring with both real offer attributes.
        harness = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const attrs = OFFERS;
const script = SCRIPT;
const cutoff = Date.parse('2026-10-31T17:00:00Z');
function visit(start) {
  let now = start;
  const events = {}, timers = [];
  const offers = attrs.map(a => ({hidden: 'hidden' in a,
    getAttribute: name => a[name], querySelector: () => null,
    classList: {add() {}}}));
  class Clock extends Date { constructor(...args) { super(...(args.length ? args : [now])); } }
  const context = {Date: Clock, document: {
    hidden: false,
    addEventListener: (name, fn) => (events[name] ||= []).push(fn),
    querySelectorAll: selector => selector === '[data-dated-offer]' ? offers : [],
    querySelector: () => null, getElementById: () => null
  }, window: {location: {hash: ''},
    addEventListener: (name, fn) => (events[name] ||= []).push(fn)},
    setTimeout: (fn, delay) => { timers.push({fn, delay}); return timers.length; },
    clearTimeout() {}};
  vm.runInNewContext(script, context);
  assert(offers.every(o => o.hidden));
  events.DOMContentLoaded.forEach(fn => fn());
  return {offers, events, timers, setTime: t => {now = t;}};
}
for (const start of [Date.parse('2026-10-14T00:00:00Z'), cutoff - 1]) {
  for (const resume of ['timer', 'visibilitychange', 'pageshow']) {
    const page = visit(start);
    assert(page.offers.every(o => !o.hidden));
    assert(page.timers.length > 0);
    assert(page.timers.every(t => t.delay <= cutoff - start));
    page.setTime(cutoff);
    (resume === 'timer' ? page.timers.map(t => t.fn) : page.events[resume]).forEach(fn => fn());
    assert(page.offers.every(o => o.hidden));
  }
}
for (const start of [cutoff, cutoff + 86400000]) {
  assert(visit(start).offers.every(o => o.hidden));
}
""".replace("OFFERS", json.dumps(offers)).replace("SCRIPT", json.dumps((ROOT / "script.js").read_text()))
        for timezone in ["Asia/Ho_Chi_Minh", "America/Los_Angeles", "Pacific/Auckland"]:
            result = subprocess.run(["node", "-e", harness], capture_output=True, text=True,
                                    env={**os.environ, "TZ": timezone})
            self.assertEqual(0, result.returncode, result.stderr)

        contract = json.loads((ROOT / "sitemap-content.json").read_text())
        for url, path, lastmod in [
            ("https://tak-12.com/", ROOT / "index.html", "2026-10-23"),
            (
                "https://tak-12.com/tak12-on-thi-lop-6/",
                ROOT / "tak12-on-thi-lop-6" / "index.html",
                "2026-10-14",
            ),
        ]:
            self.assertEqual(lastmod, contract[url]["lastmod"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), contract[url]["sha256"])
