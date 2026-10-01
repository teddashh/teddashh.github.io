#!/usr/bin/env python3
"""Screenshot a rendered project page for visual QA.

Usage:
    python3 shoot.py <repo-dir> [name] [--path sub/dir/]

Serves <repo-dir>/site on a free localhost port, captures English and
Traditional Chinese desktop views plus a Chinese mobile view with headless
Chromium, trims the empty tail, and slices each capture into readable chunks:

    ~/tmp/gh-sweep-20260930/_shots/<name>-en-desk-1.png, -2.png, ...
    ~/tmp/gh-sweep-20260930/_shots/<name>-zh-desk-1.png, ...
    ~/tmp/gh-sweep-20260930/_shots/<name>-zh-mob-1.png, ...

Prints the written file names. Look at every chunk before calling a page done.
"""

from __future__ import annotations

import http.server
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image, ImageFilter

OUT = Path.home() / "tmp" / "gh-sweep-20260930" / "_shots"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    sub = ""
    if "--path" in sys.argv:
        sub = sys.argv[sys.argv.index("--path") + 1].strip("/")
        sub = f"{sub}/" if sub else ""
        args = [a for a in args if a.strip("/") != sub.strip("/")]
    repo = Path(args[0]).resolve()
    name = args[1] if len(args) > 1 else repo.name
    site = repo / "site"
    if not (site / sub / "index.html").is_file():
        print(f"missing {site / sub / 'index.html'}; render first")
        return 1

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(site), **k)

        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    OUT.mkdir(parents=True, exist_ok=True)

    jobs = [
        ("en-desk", "1440,12000", "en", 1600),
        ("zh-desk", "1440,12000", "zh-TW", 1600),
        ("zh-mob", "390,16000", "zh-TW", 2400),
    ]
    written = []
    for label, size, lang, chunk in jobs:
        raw = OUT / f"{name}-{label}-raw.png"
        url = f"http://127.0.0.1:{port}/{sub}index.html?lang={lang}"
        # A private profile per run so parallel captures never share a browser.
        profile = Path(tempfile.mkdtemp(prefix=f".profile-{name}-", dir=OUT))
        try:
            subprocess.run(
                ["chromium", "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                 "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}",
                 "--force-device-scale-factor=1", f"--window-size={size}", "--virtual-time-budget=4000",
                 f"--screenshot={raw}", url],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180,
            )
        finally:
            shutil.rmtree(profile, ignore_errors=True)
        if not raw.is_file():
            print(f"chromium produced no screenshot for {label}")
            return 1
        img = Image.open(raw).convert("RGB")
        width, height = img.size
        # Trim the empty tail: find the lowest sharp edge (text, borders), which
        # ignores the smooth background gradients below the footer.
        edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
        box = edges.crop((2, 2, width - 2, height - 2)).point(lambda v: 255 if v > 48 else 0).getbbox()
        bottom = min(height, box[3] + 2 + 40) if box else height
        for old in OUT.glob(f"{name}-{label}-[0-9]*.png"):
            old.unlink()
        for index, top in enumerate(range(0, bottom, chunk), 1):
            part = OUT / f"{name}-{label}-{index}.png"
            img.crop((0, top, width, min(bottom, top + chunk))).save(part)
            written.append(part.name)
        raw.unlink()
    server.shutdown()
    print("\n".join(str(OUT / w) for w in written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
