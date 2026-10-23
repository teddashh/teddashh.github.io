import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent

class HTMLChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.assets = []
        self.nav_links = []
        self.in_nav = False

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if 'id' in attr_dict:
            self.ids.add(attr_dict['id'])

        if tag == 'nav':
            self.in_nav = True

        if tag == 'a' and 'href' in attr_dict:
            href = attr_dict['href']
            self.links.append(href)
            if self.in_nav:
                self.nav_links.append(href)

        if tag in ('img', 'script') and 'src' in attr_dict:
            self.assets.append(attr_dict['src'])
        if tag == 'link' and 'href' in attr_dict:
            if attr_dict.get('rel') in ('stylesheet', 'icon'):
                self.assets.append(attr_dict['href'])

    def handle_endtag(self, tag):
        if tag == 'nav':
            self.in_nav = False

class TestHTMLStructure(unittest.TestCase):
    def test_index_html(self):
        site_dir = ROOT / 'site'
        index_file = site_dir / 'index.html'
        self.assertTrue(index_file.exists())

        parser = HTMLChecker()
        parser.feed(index_file.read_text(encoding='utf-8'))

        # Validate internal anchor links
        for link in parser.links:
            if link.startswith('#'):
                self.assertIn(link[1:], parser.ids, f"Broken internal link: {link}")

        # Validate page assets
        for asset in parser.assets:
            if not asset.startswith(('http://', 'https://', 'data:')):
                asset_path = asset.split('?')[0].split('#')[0]
                if asset_path.startswith('/'):
                    asset_path = asset_path[1:]
                asset_file = site_dir / asset_path
                self.assertTrue(asset_file.exists(), f"Missing asset: {asset}")

        # Validate navigation elements
        self.assertTrue(len(parser.nav_links) > 0, "No navigation links found")
        for link in parser.nav_links:
            if link.startswith('#'):
                self.assertIn(link[1:], parser.ids, f"Broken nav link: {link}")

if __name__ == '__main__':
    unittest.main()
