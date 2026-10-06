#!/usr/bin/env python3
"""Render the project hub at https://teddashh.github.io/ from hub.json.

Usage:
    python3 kit/render_hub.py [repo-root]           # reads <repo-root>/hub.json, writes site/
    python3 kit/render_hub.py [repo-root] --check   # validate only

Shares the look, language switch, and validation rules of the project-page
kit (render.py). An optional "flows" list uses the same schema as a project
page: the same checks, the same --fd-* mapping, and flow.js plus flow.css
only when that list is present. A hub without flows renders the same files
as before. Standard library only.
"""

from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))

import render as R  # noqa: E402

HUB_URL = f"{R.SITE_ROOT}/"
CSP = ("default-src 'none'; style-src 'self'; script-src 'self'; img-src 'self' data:; "
       "connect-src 'none'; base-uri 'none'; form-action 'none'")


def validate(hub: dict) -> list[str]:
    problems: list[str] = []
    for path, text in R.walk_strings(hub):
        for char, name in R.BANNED_DASHES.items():
            if char in text:
                problems.append(f"{path}: contains an {name} ({char!r})")
        lowered = text.lower()
        for term in R.PRIVATE_TERMS:
            if term in lowered:
                problems.append(f"{path}: mentions a private or employer term {term!r}")
        if path.endswith(".zh"):
            bad = sorted({c for c in text if c in R.SIMPLIFIED_ONLY})
            if bad:
                problems.append(f"{path}: Simplified-only characters {''.join(bad)!r}")
    for path, node in R.walk_bilingual(hub):
        if not node.get("en", "").strip() or not node.get("zh", "").strip():
            problems.append(f"{path}: bilingual field needs non-empty 'en' and 'zh'")
    seen = set()
    for group in hub.get("groups", []):
        for project in group.get("projects", []):
            slug = project.get("slug")
            if slug in seen:
                problems.append(f"duplicate project {slug}")
            seen.add(slug)
            for key in ("slug", "name", "mark", "palette", "line", "stack", "status"):
                if key not in project:
                    problems.append(f"{slug}: missing {key}")
            if project.get("status") not in STATUS:
                problems.append(f"{slug}: status must be one of {sorted(STATUS)}")
    problems.extend(R.validate_flows(hub))
    return problems


STATUS = {
    "active": {"en": "Active", "zh": "持續開發"},
    "stable": {"en": "Stable", "zh": "穩定"},
    "early": {"en": "Early stage", "zh": "早期階段"},
    "paused": {"en": "Paused", "zh": "暫停開發"},
    "notes": {"en": "Notes", "zh": "筆記"},
    "utility": {"en": "Utility", "zh": "工具倉庫"},
    "toy": {"en": "Toy", "zh": "小玩具"},
}


def project_pages(project: dict) -> dict:
    page = project.get("page")
    slug = project["slug"]
    if isinstance(page, dict):
        return page
    if isinstance(page, str):
        return {"en": page, "zh": page}
    return {"en": f"/{slug}/", "zh": f"/{slug}/?lang=zh-TW"}


def per_lang_link(urls: dict, label: dict, cls: str = "") -> str:
    """Two anchors, one per language, so each language can point at its own URL."""
    c = f" {cls}" if cls else ""
    return (f'<a class="lang-en{c}" href="{R.href(urls["en"])}">{R.inline(label["en"])}</a>'
            f'<a class="lang-zh{c}" lang="zh-Hant" href="{R.href(urls["zh"])}">{R.inline(label["zh"])}</a>')


def render_card(project: dict) -> str:
    slug = project["slug"]
    urls = project_pages(project)
    status = project["status"]
    status_html = R.bi(STATUS[status], "span", f"project-status{' is-active' if status == 'active' else ''}")
    name = {"en": project["name"], "zh": project.get("name_zh", project["name"])}
    links = [per_lang_link(urls, {"en": "Project page →", "zh": "專案介紹 →"})]
    links.append(f'<a href="https://github.com/{R.OWNER}/{slug}">GitHub</a>')
    for link in project.get("links", []):
        links.append(R.anchor(link))
    return (
        f'<article class="project-card" id="p-{R.href(slug.lower())}">'
        f'<div class="project-head"><img src="tiles/{R.href(slug)}.svg" alt="" width="44" height="44">'
        f'<div><h3>{per_lang_link(urls, name)}</h3>{status_html}</div></div>'
        f'{R.bi(project["line"], "p")}'
        f'<div class="project-stack">{R.inline(project["stack"])}</div>'
        f'<div class="project-links">{"".join(links)}</div>'
        f"</article>"
    )


def render_hub(hub: dict) -> str:
    groups = hub["groups"]
    count = sum(len(g["projects"]) for g in groups)
    hero = hub["hero"]
    name = hub["name"]
    title_en = f'{name} · {R.text_of(hub["title"], "en")}'
    title_zh = f'{name} · {R.text_of(hub["title"], "zh")}'
    desc_en = R.text_of(hub["description"], "en").replace("{count}", str(count))
    desc_zh = R.text_of(hub["description"], "zh").replace("{count}", str(count))

    def fill(value):
        if R.is_bi(value):
            return {k: v.replace("{count}", str(count)) for k, v in value.items()}
        return value.replace("{count}", str(count)) if isinstance(value, str) else value

    nav_links = [f'<a href="#{g["id"]}">{R.bi(g["nav"])}</a>' for g in groups[:4]]
    if any(isinstance(item, dict) and not item.get("after") for item in (hub.get("flows") or [])):
        nav_links.append(f'<a href="#how">{R.bi({"en": "How it works", "zh": "運作方式"})}</a>')
    nav = "".join(nav_links)

    # hero visual: one row per group with its project count
    stack_cards = "".join(
        f'<div class="stack-card"><span class="stack-icon">{i:02d}</span>'
        f'<span>{R.bi(g["title_short"], "strong")}<small>{R.bi(g["summary"])}</small></span>'
        f'<span class="stack-status">{len(g["projects"])}</span></div>'
        for i, g in enumerate(groups, 1)
    )
    visual_html = (
        '<div class="visual-wrap"><div class="panel">'
        f'<div class="panel-top"><span>{R.bi({"en": "Project directory", "zh": "專案目錄"})}</span>'
        f'<span class="live-dot">{R.bi({"en": f"{count} projects", "zh": f"{count} 個專案"})}</span></div>'
        f'<div class="stack">{stack_cards}</div></div></div>'
    )

    notes = "".join(R.bi(fill(n)) if R.is_bi(n) else f"<span>{R.inline(fill(n))}</span>" for n in hero.get("notes", []))
    buttons = R.button(hero["primary"], "button-primary")
    if hero.get("secondary"):
        buttons += R.button(hero["secondary"], "button-secondary")

    parts = [
        f'<section class="hero" id="top"><div class="hero-copy">'
        f'<div class="eyebrow">{R.bi(hero["eyebrow"])}</div>'
        f'{R.bi(fill(hero["headline"]), "h1")}{R.bi(fill(hero["lede"]), "p")}'
        f'<div class="button-row">{buttons}</div>'
        + (f'<div class="hero-notes">{notes}</div>' if notes else "")
        + f"</div>{visual_html}</section>"
    ]

    stats = [dict(s, value=fill(s["value"])) for s in hub.get("stats", [])]
    if stats:
        cells = "".join(
            f'<div class="stat"><span class="stat-value">{R.inline(s["value"])}</span>'
            f'<span class="stat-label">{R.bi(s["label"])}</span></div>'
            for s in stats
        )
        parts.append(f'<div class="stats n{len(stats)}">{cells}</div>')

    for index, group in enumerate(groups):
        cards = "".join(render_card(p) for p in group["projects"])
        inner = (f'<div class="section group" id="{group["id"]}">{R.heading(group)}'
                 f'<div class="project-grid">{cards}</div></div>')
        parts.append(f'<section class="tinted">{inner}</section>' if index % 2 else f"<section>{inner}</section>")

    about = hub.get("about")
    if about:
        quote = R.bi(about["quote"], "blockquote", "quote") if about.get("quote") else ""
        parts.append(
            f'<section class="band" id="about"><div class="section problem-grid"><div>'
            f'<div class="section-kicker">{R.bi(about["kicker"])}</div>'
            f'{R.bi(about["title"], "h2")}'
            + "".join(R.bi(p, "p") for p in about["body"])
            + f"</div>{quote}</div></section>"
        )

    links = "".join(R.anchor(l) for l in hub.get("links", []))
    parts = R.place_flows(parts, hub)
    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title_en,
        "url": HUB_URL,
        "description": desc_en,
        "author": {"@type": "Person", "name": "Ted Huang", "url": "https://www.ted-h.com"},
        "hasPart": [
            {"@type": "SoftwareSourceCode", "name": p["name"], "url": R.SITE_ROOT + project_pages(p)["en"],
             "codeRepository": f"https://github.com/{R.OWNER}/{p['slug']}"}
            for g in groups for p in g["projects"]
        ],
    }
    body = "\n".join(parts)
    flow_head = ""
    if hub.get("flows"):
        flow_head = '<link rel="stylesheet" href="flow.css">\n<script src="flow.js" defer></script>\n'
    return f"""<!doctype html>
<!-- Generated from hub.json by kit/render_hub.py. Edit hub.json, then re-render. -->
<html lang="en" data-lang="en" data-title-en="{R.attr(title_en)}" data-title-zh="{R.attr(title_zh)}" data-desc-en="{R.attr(desc_en)}" data-desc-zh="{R.attr(desc_zh)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="theme-color" content="{R.palette_of(hub)['ink']}">
<title>{html.escape(title_en)}</title>
<meta name="description" content="{R.attr(desc_en)}">
<link rel="canonical" href="{HUB_URL}">
<link rel="alternate" hreflang="en" href="{HUB_URL}">
<link rel="alternate" hreflang="zh-Hant" href="{HUB_URL}?lang=zh-TW">
<link rel="alternate" hreflang="x-default" href="{HUB_URL}">
<meta property="og:type" content="website">
<meta property="og:title" content="{R.attr(title_en)}">
<meta property="og:description" content="{R.attr(desc_en)}">
<meta property="og:url" content="{HUB_URL}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="styles.css">
<script src="lang.js"></script>
<script src="app.js" defer></script>
{flow_head}<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<a class="skip-link" href="#main">{R.bi({"en": "Skip to content", "zh": "跳到主要內容"})}</a>
<header class="site-header"><div class="header-inner">
<a class="brand" href="#top"><img src="logo.svg" alt="" width="36" height="36"><span>{html.escape(name)}</span></a>
<button class="menu-button" type="button" aria-expanded="false" aria-controls="site-navigation">{R.bi({"en": "Menu", "zh": "選單"})}</button>
<nav class="site-nav" id="site-navigation" aria-label="Primary">
{nav}
<div class="language-switch" role="group" aria-label="Language / 語言"><button type="button" data-language="en" aria-pressed="true">EN</button><button type="button" data-language="zh" aria-pressed="false">繁中</button></div>
<a class="github-link" href="https://github.com/{R.OWNER}">{R.GITHUB_SVG}<span>GitHub</span></a>
</nav>
</div></header>
<main id="main">
{body}
</main>
<footer class="site-footer"><div class="footer-inner">
<div><div class="footer-brand"><img src="logo.svg" alt="" width="32" height="32"><span>{html.escape(name)}</span></div>
{R.bi(hub["title"], "p")}
<p>{R.bi({"en": "Reviewed", "zh": "最近校對"})} {html.escape(hub.get("verified", ""))} · © <span data-year>2026</span></p></div>
<div class="footer-links">{links}</div>
</div></footer>
</body>
</html>
"""


def render_404(hub: dict) -> str:
    return f"""<!doctype html>
<html lang="en" data-lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="robots" content="noindex">
<title>{html.escape(hub["name"])} · 404</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/styles.css">
<script src="/lang.js"></script>
</head>
<body>
<main class="notfound">
<div class="eyebrow">404</div>
{R.bi({"en": "This page does not exist.", "zh": "找不到這個頁面。"}, "h2")}
<p><a class="button button-primary" href="/">{R.bi({"en": "All projects", "zh": "全部專案"})}</a></p>
</main>
</body>
</html>
"""


PAGES_WORKFLOW = R.PAGES_WORKFLOW


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 and not argv[1].startswith("--") else KIT.parent
    check_only = "--check" in argv
    hub = json.loads((root / "hub.json").read_text(encoding="utf-8"))
    problems = validate(hub)
    if problems:
        print(f"hub.json: {len(problems)} problem(s)")
        for p in problems:
            print("  -", p)
        return 1
    page = render_hub(hub)
    if check_only:
        print("hub.json: ok (check only)")
        return 0
    site = root / "site"
    if site.exists():
        shutil.rmtree(site)
    (site / "tiles").mkdir(parents=True)
    pal = R.palette_of(hub)
    theme = ":root {\n" + "".join(f"  --{k.replace('accent2', 'accent-2')}: {v};\n" for k, v in pal.items()) + "}\n\n"
    css = theme + (KIT / "base.css").read_text(encoding="utf-8") + (KIT / "hub.css").read_text(encoding="utf-8")
    if hub.get("flows"):
        css += R.FLOW_MAP
    (site / "styles.css").write_text(css, encoding="utf-8")
    shutil.copyfile(KIT / "lang.js", site / "lang.js")
    shutil.copyfile(KIT / "app.js", site / "app.js")
    if hub.get("flows"):
        shutil.copyfile(KIT / "flow.js", site / "flow.js")
        shutil.copyfile(KIT / "flow.css", site / "flow.css")
    (site / "index.html").write_text(page, encoding="utf-8")
    (site / "404.html").write_text(render_404(hub), encoding="utf-8")
    (site / "logo.svg").write_text(R.logo_svg(hub["mark"], pal, 48), encoding="utf-8")
    (site / "favicon.svg").write_text(R.logo_svg(hub["mark"], pal, 64), encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")
    urls = [HUB_URL]
    for group in hub["groups"]:
        for project in group["projects"]:
            ppal = R.palette_of({"palette": project["palette"]})
            (site / "tiles" / f'{project["slug"]}.svg').write_text(R.logo_svg(project["mark"], ppal, 44), encoding="utf-8")
            urls.append(R.SITE_ROOT + project_pages(project)["en"])
    (site / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {HUB_URL}sitemap.xml\n", encoding="utf-8")
    lastmod = f"<lastmod>{hub['verified']}</lastmod>" if hub.get("verified") else ""
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{html.escape(u)}</loc>{lastmod}</url>\n" for u in urls)
        + "</urlset>\n",
        encoding="utf-8",
    )
    wf = root / ".github" / "workflows" / "pages.yml"
    if not wf.exists():
        wf.parent.mkdir(parents=True, exist_ok=True)
        wf.write_text(R.workflow_for({"default_branch": "main", "pages_extra": {"paths": ["hub.json", "kit/**"]}}), encoding="utf-8")
    print(f"rendered {site}/index.html ({len(page):,} bytes, {sum(len(g['projects']) for g in hub['groups'])} projects)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except R.PageError as exc:
        print(f"error: {exc}")
        sys.exit(1)
