#!/usr/bin/env python3
"""Print where every visible Chinese h1 / h2 / .quote wraps, as text.

Usage: python3 zh_breaks.py <repo-dir> [<repo-dir> ...] [--path sub/dir/]

Serves <repo-dir>/site on localhost, injects a same-origin probe script into
index.html (so the page CSP still applies), loads ?lang=zh-TW at desktop
(1440) and mobile (390) widths in headless Chromium, and prints each heading
as its rendered lines joined by " / ". Cheaper than reading screenshots when
the question is only "does any Chinese heading split a word".
"""

from __future__ import annotations

import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from pathlib import Path

PROBE = r"""
(function () {
  function lines(el) {
    var out = [], cur = "", top = null;
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    var range = document.createRange();
    while (walker.nextNode()) {
      var node = walker.currentNode;
      for (var i = 0; i < node.data.length; i++) {
        range.setStart(node, i); range.setEnd(node, i + 1);
        var rects = range.getClientRects();
        if (!rects.length || rects[0].width === 0) { cur += node.data[i]; continue; }
        var left = rects[0].left;
        if (top !== null && left + 1 < top) { out.push(cur.trim()); cur = ""; }
        top = left;
        cur += node.data[i];
      }
    }
    if (cur.trim()) out.push(cur.trim());
    return out;
  }
  function run() {
    var rows = [];
    document.querySelectorAll('h1, h2, .quote').forEach(function (el) {
      if (!el.offsetParent || !/[㐀-鿿]/.test(el.textContent)) return;
      rows.push(el.tagName.toLowerCase() + (el.classList.contains('quote') ? '.quote' : '') + ': ' + lines(el).join(' / '));
    });
    new Image().src = '/__report?d=' + encodeURIComponent(rows.join('\n'));
  }
  // Headless Chromium lays the page out at a 500px minimum and only shrinks
  // the window right before the capture, so measure again on resize.
  window.addEventListener('load', function () { setTimeout(run, 300); });
  window.addEventListener('resize', run);
})();
"""


def probe(site: Path, sub: str) -> dict[str, str]:
    reports: list[str] = []

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(site), **k)

        def log_message(self, *a):
            pass

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/__report":
                query = urllib.parse.urlparse(self.path).query
                reports.append(urllib.parse.parse_qs(query).get("d", [""])[0])
                self.send_response(204)
                self.end_headers()
                return
            if path == "/__probe.js":
                body = PROBE.encode()
                ctype = "text/javascript"
            elif path == f"/{sub}index.html":
                text = (site / sub / "index.html").read_text(encoding="utf-8")
                body = text.replace("</body>", '<script src="/__probe.js"></script></body>').encode()
                ctype = "text/html; charset=utf-8"
            else:
                return super().do_GET()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = {}
    # Snap-packaged Chromium can only use profile folders under your home
    # directory, outside hidden folders; same rule as shoot.py.
    shots = Path(os.environ.get("PAGE_KIT_SHOTS", Path.cwd() / "_shots")).resolve()
    shots.mkdir(parents=True, exist_ok=True)
    try:
        # Screenshot mode honours --window-size (dump-dom does not); the
        # capture itself is thrown away, the probe reports over HTTP.
        for label, size in (("desk", "1440,3000"), ("mob", "390,3000")):
            reports.clear()
            profile = Path(tempfile.mkdtemp(prefix=".probe-", dir=shots))
            scratch = profile / "probe.png"
            try:
                subprocess.run(
                    ["chromium", "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                     "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}",
                     "--force-device-scale-factor=1", f"--window-size={size}", "--virtual-time-budget=4000",
                     f"--screenshot={scratch}", f"http://127.0.0.1:{port}/{sub}index.html?lang=zh-TW"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180,
                )
            finally:
                shutil.rmtree(profile, ignore_errors=True)
            results[label] = reports[-1] if reports else "(probe produced nothing)"
    finally:
        server.shutdown()
    return results


def main(argv: list[str]) -> int:
    sub = ""
    if "--path" in argv:
        i = argv.index("--path")
        sub = argv[i + 1].strip("/") + "/"
        argv = argv[:i] + argv[i + 2:]
    for arg in argv[1:]:
        site = Path(arg).resolve() / "site"
        print(f"=== {Path(arg).name}{' /' + sub if sub else ''}")
        for label, text in probe(site, sub).items():
            print(f"[{label}]")
            print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
