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
from urllib.parse import quote
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))

import render as R  # noqa: E402
import render_hub as H  # noqa: E402

START = "<!-- projects:start -->"
END = "<!-- projects:end -->"
NOTE = "<!-- Generated from hub.json in TED-H-com/ted-h-com.github.io by kit/render_profile.py. -->"
GH = "https://github.com"
BADGE = "style=flat-square&amp;labelColor=0A2342&amp;color=0969DA"

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
    repo, name = H.project_repo(project), html.escape(project["name"], quote=True)
    out = [f'<a href="{GH}/{repo}/stargazers"><img alt="{name} stars" '
           f'src="https://img.shields.io/github/stars/{repo}?{BADGE}&amp;label=stars"></a>']
    release = project.get("release")
    if release == "latest":
        out.append(f'<a href="{GH}/{repo}/releases/latest"><img alt="{name} release" '
                   f'src="https://img.shields.io/github/v/release/{repo}?{BADGE}&amp;label=release"></a>')
    elif release == "prerelease":
        out.append(f'<a href="{GH}/{repo}/releases"><img alt="{name} release" '
                   f'src="https://img.shields.io/github/v/release/{repo}?include_prereleases&amp;{BADGE}&amp;label=release"></a>')
    return " ".join(out)



def status_badge(label: str, status: str) -> str:
    colors = {"active": "1A7F37", "stable": "1A7F37", "early": "0969DA", "paused": "465D76", "toy": "B22234", "notes": "0969DA", "utility": "0A2342"}
    url = f"https://img.shields.io/badge/{quote(label, safe='')}-{colors.get(status, '0A2342')}?style=flat-square"
    return f'<img alt="{html.escape(label, quote=True)}" src="{url}">'


def section_svg(title: str, subtitle: str = "") -> str:
    """Local, GitHub-compatible section art matching the profile hero palette."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 104" role="img" aria-label="{html.escape(title, quote=True)}">
<rect width="1000" height="104" rx="12" fill="#0A2342"/>
<path d="M12 0h976a12 12 0 0 1 12 12H0A12 12 0 0 1 12 0Z" fill="#B22234"/>
<rect x="0" y="12" width="1000" height="3" fill="#FFFFFF"/>
<rect x="24" y="34" width="5" height="43" rx="2" fill="#39D353"/>
<text x="47" y="52" fill="#FFFFFF" font-family="system-ui,Segoe UI,sans-serif" font-size="26" font-weight="700">{html.escape(title)}</text>
<text x="47" y="80" fill="#A6B8CE" font-family="system-ui,Segoe UI,sans-serif" font-size="16">{html.escape(subtitle)}</text>
<circle cx="958" cy="52" r="7" fill="#39D353"/><path d="M926 79h42" stroke="#58A6FF" stroke-width="3"/>
</svg>\n"""


def profile_chrome(text: str, lang: str) -> str:
    # These existing hand-written sections retain their claims and layout.
    headings = {"en": ("In production.", "Public work."), "zh": ("正在線上運作。", "公開作品。")}
    for key, heading in zip(("production", "public"), headings[lang]):
        image = f'<p><img src="./assets/profile-section-{key}-{lang}.svg" width="100%" alt="{heading}"></p>'
        marker = f"## {heading}"
        if image not in text:
            text = text.replace(marker, marker + "\n\n" + image)
    text = text.replace('<code>LIVE / MULTI-AI</code>', status_badge("LIVE / MULTI-AI", "active"))
    text = text.replace("https://teddashh.github.io/multi-ai-chat/", "https://ted-h-com.github.io/multi-ai-chat/")
    text = text.replace("https://teddashh.github.io/github-profile-summary-cards/", "https://ted-h-com.github.io/github-profile-summary-cards/")
    text = text.replace("https://github.com/teddashh/github-profile-summary-cards", "https://github.com/TED-H-com/github-profile-summary-cards")
    return text


def row(project: dict, lang: str) -> str:
    t = TEXT[lang]
    page = absolute(H.project_pages(project)[lang])
    status = H.STATUS[project["status"]][lang]
    chip = status.upper() if lang == "en" else status
    stack = " ".join(f"<code>{html.escape(part.strip())}</code>" for part in project["stack"].split("·"))
    links = [f'<a href="{page}">{t["page"]}</a>', f'<a href="{GH}/{H.project_repo(project)}">{t["source"]}</a>']
    for link in project.get("links", []):
        links.append(f'<a href="{html.escape(absolute(pick(link["href"], lang)), quote=True)}">{html.escape(pick(link["label"], lang))} ↗</a>')
    return f"""  <tr>
    <td width="32%" valign="top">
      <strong><a href="{page}">{html.escape(display_name(project, lang))}</a></strong><br>
      {status_badge(chip, project["status"])}
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
        parts += ["", f'<p><img src="./assets/profile-group-{group["id"]}-{lang}.svg" width="100%" alt="{html.escape(kicker, quote=True)}"></p>', "",
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
                    f"Each of these {count} repositories has its own bilingual page. "
                    f"The full directory lives at **[teddashh.github.io]({t['hub']})**.",
                    "", "| Project | What it is | Status |", "|---|---|---|"]
        else:
            head = ['<a id="traditional-chinese"></a>', "",
                    '<p align="right"><a href="../README.zh-TW.md">Ted Huang</a> / <strong>專案</strong> · '
                    '<a href="#english">English</a></p>', "", "# 專案", "",
                    f"這 {count} 個 repository 都有自己的中英雙語介紹頁。"
                    f"完整目錄在 **[teddashh.github.io]({t['hub']})**。",
                    "", "| 專案 | 內容 | 狀態 |", "|---|---|---|"]
        rows = []
        for group in hub["groups"]:
            for p in group["projects"]:
                page = absolute(H.project_pages(p)[lang])
                name = display_name(p, lang).replace("|", "\\|")
                line = p["line"][lang].replace("|", "\\|")
                rows.append(f"| **[{name}]({page})** · [{t['source']}]({GH}/{H.project_repo(p)}) | {line} | "
                            f"{H.STATUS[p['status']][lang]} |")
        sections.append("\n".join(head + rows))
    return NOTE + "\n\n" + "\n\n---\n\n".join(sections) + "\n"


def pointer(project: dict) -> str:
    pages = {lang: absolute(H.project_pages(project)[lang]) for lang in ("en", "zh")}
    shown = pages["en"].removeprefix("https://").rstrip("/")
    source = f"{GH}/{H.project_repo(project)}"
    return f"""{NOTE}

<a id="english"></a>

# {display_name(project, "en")}

This write-up moved to the project's own page: **[{shown}]({pages["en"]})**, in English and Traditional Chinese.

[Source on GitHub]({source}) · [All projects]({TEXT["en"]["hub"]}) · [Profile](../README.md)

<a id="traditional-chinese"></a>

## {display_name(project, "zh")}

這份介紹已經搬到專案自己的頁面：**[{shown}]({pages["zh"]})**，中英文都有。

[GitHub 原始碼]({source}) · [全部專案]({TEXT["zh"]["hub"]}) · [個人首頁](../README.zh-TW.md)
"""


def outputs(hub: dict, profile: Path) -> dict[Path, str]:
    files: dict[Path, str] = {}
    for name, lang in (("README.md", "en"), ("README.zh-TW.md", "zh")):
        path = profile / name
        files[path] = profile_chrome(splice(path.read_text(encoding="utf-8"), readme_block(hub, lang), path), lang)
        for group in hub["groups"]:
            files[profile / "assets" / f'profile-group-{group["id"]}-{lang}.svg'] = section_svg(group["kicker"][lang], group["summary"][lang])
        titles = {"en": (("production", "In production", "Ai-Sister Web · Multi-AI workflows"), ("public", "Public work", "Open-source projects · Verified destinations")), "zh": (("production", "正在線上運作", "Ai-Sister Web · 多 AI 工作流程"), ("public", "公開作品", "開源專案 · 已確認的專案連結"))}
        for key, title, subtitle in titles[lang]:
            files[profile / "assets" / f"profile-section-{key}-{lang}.svg"] = section_svg(title, subtitle)
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
        p.parent.mkdir(parents=True, exist_ok=True)
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
