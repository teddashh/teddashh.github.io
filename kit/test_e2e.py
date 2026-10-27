import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from html.parser import HTMLParser
import tempfile
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'kit'))
import render_hub as H

class HTMLChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if 'id' in attr_dict:
            self.ids.add(attr_dict['id'])
        if tag == 'a' and 'href' in attr_dict:
            self.links.append(attr_dict['href'])

class TestE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub = json.loads((ROOT / 'hub.json').read_text(encoding='utf-8'))
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.site_dir = Path(cls.temp_dir.name)
        (cls.site_dir / 'hub.json').write_text(json.dumps(cls.hub))
        H.main(['render_hub.py', str(cls.site_dir)])
        cls.site_path = cls.site_dir / 'site'

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_rss_feed_structure(self):
        rss_file = self.site_path / 'feed.xml'
        if not rss_file.exists():
            rss_file = self.site_path / 'rss.xml'

        self.assertTrue(rss_file.exists(), "RSS feed file (feed.xml or rss.xml) not found in generated site")

        tree = ET.parse(rss_file)
        root = tree.getroot()

        self.assertEqual(root.tag, 'rss', "Root element should be 'rss'")
        self.assertEqual(root.attrib.get('version'), '2.0', "RSS version should be 2.0")

        channel = root.find('channel')
        self.assertIsNotNone(channel, "RSS feed must contain a 'channel' element")

        title = channel.find('title')
        self.assertIsNotNone(title, "Channel must have a 'title'")

        link = channel.find('link')
        self.assertIsNotNone(link, "Channel must have a 'link'")

        description = channel.find('description')
        self.assertIsNotNone(description, "Channel must have a 'description'")

        items = channel.findall('item')
        self.assertGreater(len(items), 0, "RSS feed should have at least one 'item'")

        for item in items:
            self.assertIsNotNone(item.find('title'), "Item must have a 'title'")
            self.assertIsNotNone(item.find('link'), "Item must have a 'link'")

    def test_sitemap_generation(self):
        sitemap_file = self.site_path / 'sitemap.xml'
        self.assertTrue(sitemap_file.exists(), "sitemap.xml not found in generated site")

        tree = ET.parse(sitemap_file)
        root = tree.getroot()

        self.assertTrue(root.tag.endswith('urlset'), "Root element should be 'urlset'")
        self.assertIn('sitemaps.org/schemas/sitemap', root.tag, "Missing correct xmlns")

        urls = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
        self.assertGreater(len(urls), 0, "Sitemap should contain at least one 'url' element")

        for url_elem in urls:
            loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            self.assertIsNotNone(loc, "Each 'url' must have a 'loc'")
            self.assertTrue(loc.text.startswith('http'), "loc text should be a valid URL")

    def test_internal_anchor_hrefs(self):
        index_file = self.site_path / 'index.html'
        self.assertTrue(index_file.exists())

        parser = HTMLChecker()
        parser.feed(index_file.read_text(encoding='utf-8'))

        for link in parser.links:
            if link.startswith('#') and len(link) > 1:
                target_id = link[1:]
                self.assertIn(target_id, parser.ids, f"Internal anchor href '{link}' points to non-existent id.")
