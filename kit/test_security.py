import unittest
from pathlib import Path
from html.parser import HTMLParser
import json
import tempfile
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'kit'))
import render_hub as H

class SecurityParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.scripts = []
        self.stylesheets = []
        self.meta_redirects = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == 'a' and 'href' in attr_dict:
            self.links.append((attr_dict['href'], attr_dict.get('rel', '')))
        elif tag == 'script' and 'src' in attr_dict:
            self.scripts.append(attr_dict)
        elif tag == 'link' and attr_dict.get('rel') == 'stylesheet' and 'href' in attr_dict:
            self.stylesheets.append(attr_dict)
        elif tag == 'meta' and attr_dict.get('http-equiv', '').lower() == 'refresh':
            content = attr_dict.get('content', '')
            if ';' in content:
                url_part = content.split(';', 1)[1].strip()
                if url_part.lower().startswith('url='):
                    self.meta_redirects.append(url_part[4:])

class TestSecurity(unittest.TestCase):
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

    def test_outbound_links_have_noopener_noreferrer(self):
        for html_file in self.site_path.rglob("*.html"):
            parser = SecurityParser()
            parser.feed(html_file.read_text(encoding='utf-8'))

            for href, rel in parser.links:
                if href.startswith('http'):
                    self.assertIn('noopener', rel, f"Missing 'noopener' in rel for outbound link {href} in {html_file}")
                    self.assertIn('noreferrer', rel, f"Missing 'noreferrer' in rel for outbound link {href} in {html_file}")

    def test_meta_refresh_redirects_are_safe(self):
        for html_file in self.site_path.rglob("*.html"):
            parser = SecurityParser()
            parser.feed(html_file.read_text(encoding='utf-8'))

            for url in parser.meta_redirects:
                parsed = urlparse(url)
                # Should be either absolute safe schema or a relative path
                if parsed.scheme:
                    self.assertIn(parsed.scheme, ['http', 'https'], f"Unsafe scheme in meta refresh {url} in {html_file}")
                else:
                    self.assertTrue(url.startswith('/'), f"Unsafe relative meta refresh {url} in {html_file}")

    def test_external_resources_have_sri(self):
        for html_file in self.site_path.rglob("*.html"):
            parser = SecurityParser()
            parser.feed(html_file.read_text(encoding='utf-8'))

            for script in parser.scripts:
                src = script['src']
                if src.startswith('http'):
                    self.assertIn('integrity', script, f"Missing SRI (integrity) on external script {src} in {html_file}")

            for style in parser.stylesheets:
                href = style['href']
                if href.startswith('http'):
                    self.assertIn('integrity', style, f"Missing SRI (integrity) on external stylesheet {href} in {html_file}")

    def test_moved_js_uses_url_api_for_sanitization(self):
        moved_js_path = self.site_path / 'moved.js'
        if moved_js_path.exists():
            content = moved_js_path.read_text(encoding='utf-8')
            self.assertIn('new URL(', content, "moved.js does not use URL API for sanitization")
            self.assertIn('.origin ===', content, "moved.js does not validate origin against expected target")

if __name__ == '__main__':
    unittest.main()
