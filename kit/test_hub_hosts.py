"""Host-specific rendering and legacy URL regression checks (standard library)."""
import json
from pathlib import Path
import tempfile
import unittest
import render_hub as H

ROOT = Path(__file__).resolve().parent.parent
LEGACY = {'AI-Intune', 'AI-Sister', 'TokenMonster', 'ai-brainstorming',
          'ai-security-scanner', 'claude-idea-review-skill', 'mcp-memory-server',
          'multi-ai-chat', 'multi-ai-chat-desktop', 'multi-ai-terminal',
          'reset-therapy', 'zhan-dou-tuo-luo'}

class HostTests(unittest.TestCase):
    def test_both_hosts(self):
        hub = json.loads((ROOT / 'hub.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'hub.json').write_text(json.dumps(hub))
            for host in ('teddashh', 'ted-h-com'):
                H.main(['render_hub.py', str(root), '--site-owner', host])
                site = root / 'site'
                origin = f'https://{host}.github.io'
                index = (site / 'index.html').read_text()
                self.assertIn(f'<link rel="canonical" href="{origin}/">', index)
                self.assertIn(f'{origin}/sitemap.xml', (site / 'robots.txt').read_text())
                self.assertIn('href="https://github.com/teddashh"', index)
                moved = H.moved_pages(hub)
                self.assertTrue(all(target != origin for _, target in moved.values()))
                for slug in LEGACY:
                    self.assertEqual((site / slug / 'index.html').exists(), host == 'teddashh')
                if host == 'teddashh':
                    self.assertTrue(LEGACY.issubset(moved))
                    script = (site / 'moved.js').read_text()
                    self.assertIn('window.location.search + window.location.hash', script)
                    self.assertIn('window.location.origin', script)
                    self.assertIn('src="/moved.js"', (site / '404.html').read_text())

    def test_explicit_same_host_move_not_redirected(self):
        previous = H.SITE_ROOT
        try:
            H.SITE_ROOT = 'https://ted-h-com.github.io'
            self.assertEqual(H.moved_pages({'groups': [], 'moved': ['TED-H-com/example']}), {})
        finally:
            H.SITE_ROOT = previous

    def test_explicit_page_not_redirected(self):
        previous = H.SITE_ROOT
        try:
            H.SITE_ROOT = 'https://teddashh.github.io'
            project = {'slug': 'example', 'name': 'Example', 'repo': 'TED-H-com/example'}
            self.assertIn('example', H.moved_pages({'groups': [{'projects': [project]}]}))
            project['page'] = 'https://github.com/TED-H-com/example#readme'
            self.assertEqual(H.moved_pages({'groups': [{'projects': [project]}]}), {})
        finally:
            H.SITE_ROOT = previous

if __name__ == '__main__':
    unittest.main()
