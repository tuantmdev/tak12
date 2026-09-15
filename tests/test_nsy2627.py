import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://tak12.com/news/n/2486/chao-mung-nam-hoc-moi-26-27-tang-ma-giam-20-va-thoi-han-pro?ref=njg2odn'


class OfferParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.offer = None
        self.inside = False
        self.links = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id') == 'nsy2627':
            self.offer = attrs
            self.inside = True
        if self.inside and tag == 'a':
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'section':
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.text.append(data)


class CampaignTests(unittest.TestCase):
    def test_verified_offer_is_scoped_dated_and_tracks_both_destinations(self):
        html = (ROOT / 'tak12-ma-giam-gia/index.html').read_text()
        parser = OfferParser()
        parser.feed(html)
        self.assertIsNotNone(parser.offer, 'Missing verified campaign section')
        assert parser.offer is not None
        self.assertIn('hidden', parser.offer, 'Fail closed without JavaScript')
        self.assertEqual('20/09/2026', parser.offer['data-end-date'])
        text = ' '.join(parser.text)
        for marker in ['NSY2627', 'giảm 20%', 'PRO', 'không áp dụng', 'credit (xu)', 'Speaking', 'Writing', '21/09/2026', 'từ 01 năm', 'Asia/Ho_Chi_Minh', 'Sử dụng mã học bổng', 'Áp dụng', 'captcha']:
            self.assertIn(marker, text)
        self.assertEqual(2, len(parser.links))
        self.assertEqual(SOURCE, parser.links[0]['href'])
        self.assertEqual('campaign_nsy2627', parser.links[0]['data-intent'])
        self.assertEqual('https://tak12.com/info/bang-gia?ref=njg2odn', parser.links[1]['href'])
        for link in parser.links:
            self.assertEqual({'sponsored', 'noopener'}, set(link['rel'].split()))
            self.assertTrue(link['data-cta'])
        self.assertNotIn('NSY2627', html.split('</head>')[0])

    def test_verified_popular_packages_are_published_only_inside_dated_offer(self):
        html = (ROOT / 'tak12-ma-giam-gia/index.html').read_text(encoding='utf-8')
        offer = html[html.index('id="nsy2627"'):html.index('</section>', html.index('id="nsy2627"'))]
        before_offer = html[:html.index('id="nsy2627"')]
        after_offer = html[html.index('</section>', html.index('id="nsy2627"')):]

        for marker in [
            '712.000đ', '13 tháng', 'khoảng 55.000đ/tháng',
            '1.832.000đ', '65 tháng', 'khoảng 28.000đ/tháng',
            '2.600.000đ', '52 tháng', '50.000đ/tháng',
            '2.944.000đ', 'khoảng 45.000đ/tháng',
            '2.280.000đ', '30/06/2027',
            '2.896.000đ', '30/06/2028',
        ]:
            self.assertIn(marker, offer)
            self.assertNotIn(marker, before_offer)
            self.assertNotIn(marker, after_offer)

        self.assertEqual(6, offer.count('class="offer-package"'))
        self.assertIn('Giá ưu đãi sau khi áp dụng mã', offer)
        self.assertIn('kiểm tra lại giá, thời hạn và nội dung gói', offer)

        source_image = ROOT / 'docs/nsy2627-top-packages.jpg'
        self.assertTrue(source_image.is_file(), 'Owner-supplied package graphic must remain auditable')
        source_notes = (ROOT / 'docs/nsy2627-source.md').read_text(encoding='utf-8')
        self.assertIn('nsy2627-top-packages.jpg', source_notes)
