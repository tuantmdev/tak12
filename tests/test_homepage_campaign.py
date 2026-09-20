import unittest
from pathlib import Path
from html.parser import HTMLParser
ROOT = Path(__file__).resolve().parents[1]

class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.tags = []; self.feed(html)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

class HomepageCampaignTests(unittest.TestCase):
    def test_existing_homepage_campaign_slot_is_dated_and_attributed(self):
        html = (ROOT / 'index.html').read_text()
        tags = Tags(html).tags
        offer = next((a for t,a in tags if a.get('id') == 'homepage-nsy2627'), None)
        self.assertIsNotNone(offer, 'Missing homepage campaign slot')
        self.assertIn('campaign-carousel', offer['class'])
        self.assertIn('hidden', offer)
        self.assertIn('data-dated-offer', offer)
        self.assertEqual('20/09/2026', offer['data-end-date'])
        self.assertLess(html.index('id="homepage-nsy2627"'), html.index('id="courses-section"'))
        for text in ['NSY2627', 'giảm 20%', 'Speaking', 'Writing', 'credit (xu)', '/tak12-ma-giam-gia/#nsy2627']:
            self.assertIn(text, html)
        for marker in [
            'class="campaign-countdown"',
            'data-campaign-days-block',
            'data-campaign-days',
            'data-campaign-timer-block',
            'data-timer-h',
            'data-timer-m',
            'data-timer-s',
        ]:
            self.assertIn(marker, html, f'Missing countdown marker: {marker}')
        countdown = next(a for t, a in tags if 'campaign-countdown' in a.get('class', '').split())
        self.assertEqual('timer', countdown.get('role'))
        self.assertNotIn('aria-live', countdown, 'A one-second timer must not create screen-reader chatter')
        link = next(a for t,a in tags if a.get('data-cta') == 'homepage_nsy2627_pricing')
        self.assertEqual('https://tak12.com/info/bang-gia?ref=njg2odn', link['href'])
        self.assertEqual('verify-current-price-and-access', link['data-intent'])
        self.assertEqual({'sponsored','noopener'}, set(link['rel'].split()))

    def test_seo_llm_and_keyword_surfaces_are_scoped_and_date_safe(self):
        html = (ROOT / 'index.html').read_text()
        tags = Tags(html).tags
        for key, value in [('name', 'description'), ('property', 'og:description'), ('name', 'twitter:description')]:
            meta = next(a for t,a in tags if t == 'meta' and a.get(key) == value)
            self.assertIn('mã giảm giá TAK12', meta['content'])
            self.assertIn('mã học bổng', meta['content'])
            self.assertNotIn('20%', meta['content'])
        keywords = next(a for t,a in tags if t == 'meta' and a.get('name') == 'keywords')
        self.assertIn('mã giảm giá TAK12', keywords['content'])
        self.assertIn('mã học bổng TAK12', keywords['content'])
        self.assertIn('<title>TAK12: Đánh Giá Độc Lập &amp; Chọn Chương Trình</title>', html)
        llms = (ROOT / 'llms.txt').read_text()
        for marker in ['NSY2627', '20%', '2026-09-21T00:00:00+07:00', 'Speaking/Writing', 'Không suy diễn', '/tak12-ma-giam-gia/#nsy2627', '/news/n/2486/']:
            self.assertIn(marker, llms)
        mapping = (ROOT / 'docs/keyword-map.md').read_text()
        for marker in ['NSY2627', '/#homepage-nsy2627', '/tak12-ma-giam-gia/', '20/09/2026']:
            self.assertIn(marker, mapping)

if __name__ == '__main__': unittest.main()
