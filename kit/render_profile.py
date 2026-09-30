#!/usr/bin/env python3
"""Render the project sections of the GitHub profile README from hub.json.

Usage:
    python3 kit/render_profile.py <profile-repo>           # write
    python3 kit/render_profile.py <profile-repo> --check   # exit 1 if anything is out of date

Writes inside <profile-repo>:
    README.md, README.zh-TW.md   only the block between <!-- projects:start -->
                                 and <!-- projects:end -->; the rest stays hand-written
    projects/README.md           a bilingual directory of every project page
    projects/<name>.md           a short pointer for each older write-up that
                                 already exists there (matched to a slug, ignoring case)

Reads hub.json from the repository root next to kit/. Standard library only.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))

import render as R  # noqa: E402
import render_hub as H  # noqa: E402

START = "<!-- projects:start -->"
END = "<!-- projects:end -->"
NOTE = "<!-- Generated from hub.json in teddashh/teddashh.github.io by kit/render_profile.py. -->"
GH = f"https://github.com/{R.OWNER}"
BADGE = "style=flat-square&amp;color=111111"

TEXT = {
    "en": {
        "intro": "{count} original public repositories in four groups. Each title opens the project's own "
                 "page in English and Traditional Chinese, with an honest status section. Badges are live.",
        "page": "Project page ↗",
        "source": "Source ↗",
        "all": "All {count} project pages →",
        "hub": f"{R.SITE_ROOT}/",
        "readme": "../README.md",
    },
    "zh": {
        "intro": "{count} 個原創公開專案，分成四組。點標題會打開該專案自己的中英雙語介紹頁，"
                 "頁面裡也老實寫出目前的狀態。徽章都是即時的。",
        "page": "專案介紹 ↗",
        "source": "原始碼 ↗",
        "all": "全部 {count} 個專案介紹頁 →",
        "hub": f"{R.SITE_ROOT}/?lang=zh-TW",
        "readme": "../README.zh-TW.md",
    },
}


def absolute(url: str) -> str:
    return R.SITE_ROOT + url if url.startswith("/") else url


def pick(value, lang: str) -> str:
    return value[lang] if R.is_bi(value) else value


def display_name(project: dict, lang: str) -> str:
    return project.get("name_zh", project["name"]) if lang == "zh" else project["name"]


def badges(project: dict) -> str:
    slug, name = project["slug"], html.escape(project["name"], quote=True)
    out = [f'<a href="{GH}/{slug}/stargazers"><img alt="{name} stars" '
           f'src="https://img.shields.io/github/stars/{R.OWNER}/{slug}?{BADGE}&amp;label=stars"></a>']
    release = project.get("release")
    if release == "latest":
        out.append(f'<a href="{GH}/{slug}/releases/latest"><img alt="{name} release" '
                   f'src="https://img.shields.io/github/v/release/{R.OWNER}/{slug}?{BADGE}&amp;label=release"></a>')
    elif release == "prerelease":
        out.append(f'<a href="{GH}/{slug}/releases"><img alt="{name} release" '
                   f'src="https://img.shields.io/github/v/release/{R.OWNER}/{slug}?include_prereleases&amp;{BADGE}&amp;label=release"></a>')
    return " ".join(out)


def row(project: dict, lang: str) -> str:
    t = TEXT[lang]
    slug = project["slug"]
    page = absolute(H.project_pages(project)[lang])
    status = H.STATUS[project["status"]][lang]
    chip = status.upper() if lang == "en" else status
    stack = " ".join(f"<code>{html.escape(part.strip())}</code>" for part in project["stack"].split("·"))
    links = [f'<a href="{page}">{t["page"]}</a>', f'<a href="{GH}/{slug}">{t["source"]}</a>']
    for link in project.get("links", []):
        links.append(f'<a href="{html.escape(absolute(link["href"]), quote=True)}">{html.escape(pick(link["label"], lang))} ↗</a>')
    return f"""  <tr>
    <td width="32%" valign="top">
      <strong><a href="{page}">{html.escape(display_name(project, lang))}</a></strong><br>
      <code>{html.escape(chip)}</code>
    </td>
    <td width="68%" valign="top">
      {R.inline(project["line"][lang])}<br><br>
      {badges(project)}<br><br>
      {stack}<br><br>
      {" · ".join(links)}
    </td>
  </tr>"""


def readme_block(hub: dict, lang: str) -> str:
    t = TEXT[lang]
    count = sum(len(g["projects"]) for g in hub["groups"])
    parts = [START, NOTE, "", t["intro"].replace("{count}", str(count))]
    for group in hub["groups"]:
        kicker = group["kicker"][lang].replace(" · ", " / ")
        parts += ["", f"<p><code>{html.escape(kicker.upper() if lang == 'en' else kicker)}</code></p>", "",
                  '<table width="100%">', "\n".join(row(p, lang) for p in group["projects"]), "</table>"]
    parts += ["", f'<p align="right"><a href="{t["hub"]}"><strong>{t["all"].replace("{count}", str(count))}</strong></a></p>', END]
    return "\n".join(parts)


def splice(text: str, block: str, path: Path) -> str:
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
        raise R.PageError(f"{path}: needs exactly one {START} ... {END} block")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    return head + block + tail


def directory(hub: dict) -> str:
    count = sum(len(g["projects"]) for g in hub["groups"])
    sections = []
    for lang in ("en", "zh"):
        t = TEXT[lang]
        if lang == "en":
            head = ['<a id="english"></a>', "",
                    '<p align="right"><a href="../README.md">Ted Huang</a> / <strong>Projects</strong> · '
                    '<a href="#traditional-chinese">繁體中文</a></p>', "", "# Projects", "",
                    f"Each of these {count} repositories has its own bilingual page on GitHub Pages. "
                    f"The full directory lives at **[teddashh.github.io]({t['hub']})**.",
                    "", "| Project | What it is | Status |", "|---|---|---|"]
        else:
            head = ['<a id="traditional-chinese"></a>', "",
                    '<p align="right"><a href="../README.zh-TW.md">Ted Huang</a> / <strong>專案</strong> · '
                    '<a href="#english">English</a></p>', "", "# 專案", "",
                    f"這 {count} 個 repository 在 GitHub Pages 上都有自己的中英雙語介紹頁。"
                    f"完整目錄在 **[teddashh.github.io]({t['hub']})**。",
                    "", "| 專案 | 內容 | 狀態 |", "|---|---|---|"]
        rows = []
        for group in hub["groups"]:
            for p in group["projects"]:
                page = absolute(H.project_pages(p)[lang])
                name = display_name(p, lang).replace("|", "\\|")
                line = p["line"][lang].replace("|", "\\|")
                rows.append(f"| **[{name}]({page})** · [{t['source']}]({GH}/{p['slug']}) | {line} | "
                            f"{H.STATUS[p['status']][lang]} |")
        sections.append("\n".join(head + rows))
    return NOTE + "\n\n" + "\n\n---\n\n".join(sections) + "\n"


def pointer(project: dict) -> str:
    pages = {lang: absolute(H.project_pages(project)[lang]) for lang in ("en", "zh")}
    shown = pages["en"].removeprefix("https://").rstrip("/")
    slug = project["slug"]
    return f"""{NOTE}

<a id="english"></a>

# {display_name(project, "en")}

This write-up moved to the project's own page: **[{shown}]({pages["en"]})**, in English and Traditional Chinese.

[Source on GitHub]({GH}/{slug}) · [All projects]({TEXT["en"]["hub"]}) · [Profile](../README.md)

<a id="traditional-chinese"></a>

## {display_name(project, "zh")}

這份介紹已經搬到專案自己的頁面：**[{shown}]({pages["zh"]})**，中英文都有。

[GitHub 原始碼]({GH}/{slug}) · [全部專案]({TEXT["zh"]["hub"]}) · [個人首頁](../README.zh-TW.md)
"""


def outputs(hub: dict, profile: Path) -> dict[Path, str]:
    files: dict[Path, str] = {}
    for name, lang in (("README.md", "en"), ("README.zh-TW.md", "zh")):
        path = profile / name
        files[path] = splice(path.read_text(encoding="utf-8"), readme_block(hub, lang), path)
    files[profile / "projects" / "README.md"] = directory(hub)
    by_slug = {p["slug"].lower(): p for g in hub["groups"] for p in g["projects"]}
    for path in sorted((profile / "projects").glob("*.md")):
        if path.name == "README.md":
            continue
        project = by_slug.get(path.stem.lower())
        if project is None:
            raise R.PageError(f"{path}: no project in hub.json matches this file name")
        files[path] = pointer(project)
    for path, text in files.items():
        for char, label in R.BANNED_DASHES.items():
            if char in text:
                raise R.PageError(f"{path}: generated text contains an {label}")
    return files


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    profile = Path(args[0]).resolve()
    hub = json.loads((KIT.parent / "hub.json").read_text(encoding="utf-8"))
    problems = H.validate(hub)
    if problems:
        print(f"hub.json: {len(problems)} problem(s)")
        for p in problems:
            print("  -", p)
        return 1
    files = outputs(hub, profile)
    stale = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if "--check" in argv:
        for p in stale:
            print(f"out of date: {p.relative_to(profile)}")
        print("profile: ok" if not stale else f"profile: {len(stale)} file(s) out of date")
        return 1 if stale else 0
    for p in stale:
        p.write_text(files[p], encoding="utf-8")
        print(f"wrote {p.relative_to(profile)}")
    print(f"profile: {len(stale)} file(s) updated, {len(files) - len(stale)} unchanged")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except R.PageError as exc:
        print(f"error: {exc}")
        sys.exit(1)
