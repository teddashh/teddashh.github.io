#!/usr/bin/env python3
"""Render a bilingual (English / Traditional Chinese) GitHub Pages project page.

Usage:
    python3 render.py <repo-dir>             # reads <repo-dir>/site/page.json
    python3 render.py <repo-dir> --check     # validate only, write nothing

The page source of truth is site/page.json. Everything else in site/ is
generated: index.html, 404.html, styles.css, lang.js, app.js, logo.svg,
favicon.svg, robots.txt, sitemap.xml, .nojekyll, and copied screenshots
under site/assets/. Pages that set "flows" also get flow.js and flow.css.
The GitHub Actions workflow is written to .github/workflows/pages.yml
unless one already exists.

Standard library only.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
OWNER = "teddashh"
HUB = f"https://{OWNER}.github.io/"
SITE_ROOT = f"https://{OWNER}.github.io"

PALETTES = {
    "lime":     dict(ink="#111d19", paper="#f3f0e7", accent="#e9f66f", accent2="#a8c7fa", signal="#ff6b4a", kicker="#287558"),
    "violet":   dict(ink="#1b1530", paper="#f5f2ee", accent="#dccbff", accent2="#ffc9e3", signal="#7c3aed", kicker="#5b3cc4"),
    "teal":     dict(ink="#0f2226", paper="#f0f4f1", accent="#a3ecd9", accent2="#ffd9a8", signal="#0f8f78", kicker="#0d7564"),
    "amber":    dict(ink="#1f170b", paper="#f6f0e4", accent="#ffd166", accent2="#bcd8ff", signal="#e4572e", kicker="#94580a"),
    "rose":     dict(ink="#24121b", paper="#f7efef", accent="#ffc4d6", accent2="#c9e4ff", signal="#d6006e", kicker="#a3124f"),
    "blue":     dict(ink="#0f1828", paper="#eff2f6", accent="#bcd6ff", accent2="#f3e27c", signal="#2f6fed", kicker="#1f4fb8"),
    "graphite": dict(ink="#141414", paper="#f3f3f0", accent="#e4e4de", accent2="#cad5ff", signal="#ff5a36", kicker="#4a4a4a"),
    "ember":    dict(ink="#1c1210", paper="#f6efe9", accent="#ffb9a3", accent2="#ffe39e", signal="#d63a2f", kicker="#a1271e"),
    "moss":     dict(ink="#16200f", paper="#f2f1e6", accent="#cfe8a0", accent2="#f5c8a8", signal="#5f8f1f", kicker="#4b7518"),
}

ALLOWED_LEVELS = {"critical", "high", "medium", "ok", "info", "muted"}
ALLOWED_STATES = {"ok", "wait", "warn", "fail"}
ALLOWED_TERM = {"cmd", "out", "ok", "warn", "err", "dim"}
FLOW_TONES = {"neutral", "accent", "warn", "info"}
FLOW_ICONS = {
    "chat", "route", "spark", "shield", "mask", "cloud", "check", "ledger",
    "search", "people", "pool", "clock", "forward", "window", "database",
    "hub", "wallet", "code", "terminal", "user", "gear", "lock", "doc",
    "bolt", "globe", "eye", "key", "upload", "download", "bell", "image",
    "music", "game",
}


def _rgb(value: object, key: str) -> tuple[int, int, int]:
    if isinstance(value, str) and re.fullmatch(r"#(?:[0-9a-fA-F]{3}){1,2}", value):
        digits = value[1:] if len(value) == 7 else "".join(c * 2 for c in value[1:])
        return tuple(int(digits[i:i + 2], 16) for i in (0, 2, 4))
    raise PageError(f"palette color {key} must be #rgb or #rrggbb, got {value!r}")


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{v:02x}" for v in rgb)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], p: float) -> str:
    """color-mix(in srgb, a p, b) as a #rrggbb value."""
    return _hex(tuple(int(x * p + y * (1 - p) + 0.5) for x, y in zip(a, b)))


# Appended to styles.css only when a page has flows. Signal and accent-2 are
# too light to be small text on paper, so accent text and info are mixed
# toward ink until they clear 4.5:1. The bright signal stays --fd-accent
# for the rails, halo, and pulse. The mixes are worked out here and written
# as plain colors, because flow.css mixes these tones again and WebKit 26.5
# crashes on a color-mix() whose two colors are both color-mix() values.
def flow_map(pal: dict) -> str:
    ink, paper, accent2, signal, kicker = (
        _rgb(pal.get(k), k) for k in ("ink", "paper", "accent2", "signal", "kicker")
    )
    return f"""
.fd {{
  --fd-surface: {_mix(paper, (255, 255, 255), 0.35)};
  --fd-edge: rgb({ink[0]} {ink[1]} {ink[2]} / 0.14);
  --fd-text: {_hex(ink)};
  --fd-faint: {_mix(ink, paper, 0.52)};
  --fd-accent: {_hex(signal)};
  --fd-accent-ink: {_mix(signal, ink, 0.6)};
  --fd-warn: {_hex(kicker)};
  --fd-info: {_mix(accent2, ink, 0.4)};
  --fd-font: inherit;
  --fd-mono: var(--mono);
}}
"""

BANNED_DASHES = {"\u2014": "em-dash", "\u2015": "horizontal bar", "\u2013": "en-dash"}


def load_private_terms() -> list[str]:
    """Terms that must never appear on a public page (private repo names, host
    names, employer names). Kept out of this public file: one term per line in
    kit/private-terms.txt (gitignored) or in $PAGE_KIT_PRIVATE_TERMS."""
    import os
    path = Path(os.environ.get("PAGE_KIT_PRIVATE_TERMS", KIT / "private-terms.txt"))
    if not path.is_file():
        return []
    return [line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


PRIVATE_TERMS = load_private_terms()
# Characters that exist only in Simplified Chinese. Their presence in a zh field
# almost always means the copy slipped out of Traditional Chinese (Taiwan).
SIMPLIFIED_ONLY = set(
    "这个们说时实发开关数据与为对应设计务让还进过运经统网络线页读写译语认证录复杂权标题类种质项业际产馈档软码库储动态装载启错误测试验条术机兴图释简单长门问间闭显见观视觉规则达选择边点击链连续级组织结构现场报处执传输资讯汇总账号环变换决议论备么吗给从会来东车马书学习买卖战轮赛胜负积云后"
)

INLINE_TAG = re.compile(r"&lt;(/?)(em|strong|code|br)\s*/?&gt;")
SHORT_CODE = re.compile(r"<code>([^<]{1,80})</code>")
INLINE_LINK = re.compile(r"&lt;a href=&quot;((?:https?://|\./|\.\./|#|mailto:)[^&\"<>\s]*)&quot;&gt;")


class PageError(Exception):
    pass


# ----------------------------------------------------------------------------
# validation
# ----------------------------------------------------------------------------

def walk_strings(node, path="$"):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from walk_strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_strings(value, f"{path}[{index}]")


def validate(page: dict) -> list[str]:
    problems: list[str] = []
    for path, text in walk_strings(page):
        for char, name in BANNED_DASHES.items():
            if char in text:
                problems.append(f"{path}: contains an {name} ({char!r}); use a comma, colon, or plain hyphen")
        lowered = text.lower()
        for term in PRIVATE_TERMS:
            if term in lowered:
                problems.append(f"{path}: mentions a private or employer term {term!r}")
        if re.search(r"(?:^|\.)zh(?:$|\[)", path) and not re.search(r"(?:^|\.)href\.zh(?:$|\[)", path):
            bad = sorted({c for c in text if c in SIMPLIFIED_ONLY})
            if bad:
                problems.append(f"{path}: Simplified-only characters {''.join(bad)!r}; use Traditional Chinese (Taiwan)")
            if len(text) > 24 and not re.search(r"[一-鿿]", text):
                problems.append(f"{path}: zh text has no Chinese characters")
    for path, node in walk_bilingual(page):
        if not node.get("en", "").strip() or not node.get("zh", "").strip():
            problems.append(f"{path}: bilingual field needs non-empty 'en' and 'zh'")
    for key in ("repo", "slug", "name", "mark", "title", "description", "hero", "capabilities", "status", "facts"):
        if key not in page:
            problems.append(f"$.{key}: required")
    if page.get("slug") and page.get("repo") and page["repo"].split("/")[-1] != page["slug"]:
        problems.append("$.slug must equal the repository name (GitHub Pages path is case-sensitive)")
    if page.get("mark") and not (1 <= len(page["mark"]) <= 3):
        problems.append("$.mark: 1 to 3 characters")
    items = page.get("capabilities", {}).get("items", [])
    if items and len(items) not in (3, 6):
        problems.append("$.capabilities.items: use exactly 3 or 6 cards")
    flow = page.get("flow")
    if flow and not (2 <= len(flow.get("steps", [])) <= 4):
        problems.append("$.flow.steps: 2 to 4 steps")
    stats = page.get("stats") or []
    if stats and not (2 <= len(stats) <= 4):
        problems.append("$.stats: 2 to 4 items")
    arch = page.get("architecture")
    if arch and not (2 <= len(arch.get("nodes", [])) <= 4):
        problems.append("$.architecture.nodes: 2 to 4 nodes")
    visual = page.get("hero", {}).get("visual", {})
    vtype = visual.get("type")
    if vtype not in {"receipt", "terminal", "report", "chat", "stack", "image"}:
        problems.append("$.hero.visual.type: one of receipt, terminal, report, chat, stack, image")
    for row in visual.get("rows", []) if vtype == "receipt" else []:
        if row.get("state", "ok") not in ALLOWED_STATES:
            problems.append(f"receipt row state must be one of {sorted(ALLOWED_STATES)}")
    for row in visual.get("rows", []) if vtype == "report" else []:
        if row.get("level", "info") not in ALLOWED_LEVELS:
            problems.append(f"report row level must be one of {sorted(ALLOWED_LEVELS)}")
    for line in visual.get("lines", []) if vtype == "terminal" else []:
        if line.get("kind", "out") not in ALLOWED_TERM:
            problems.append(f"terminal line kind must be one of {sorted(ALLOWED_TERM)}")
    problems.extend(validate_flows(page))
    return problems


def walk_bilingual(node, path="$"):
    if isinstance(node, dict):
        if set(node) <= {"en", "zh"} and (set(node) & {"en", "zh"}):
            if all(isinstance(value, str) for value in node.values()):
                yield path, node
                return
        for key, value in node.items():
            yield from walk_bilingual(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_bilingual(value, f"{path}[{index}]")


def _index(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _section_exists(page: dict, sid: str) -> bool:
    if sid in {"top", "features", "status"}:
        return True
    if sid == "about":
        return bool(page.get("about"))
    if sid == "how":
        return bool(page.get("flow"))
    if sid == "screens":
        return bool(page.get("showcase"))
    if sid == "architecture":
        return bool(page.get("architecture"))
    if sid == "decisions":
        return bool(page.get("decisions"))
    if sid == "start":
        return bool(page.get("quickstart"))
    return False


def validate_flows(page: dict) -> list[str]:
    flows = page.get("flows")
    if flows is None:
        return []
    if not isinstance(flows, list):
        return ["$.flows: must be a list"]
    problems: list[str] = []
    seen: set[str] = set()
    reserved = {"top", "how", "features", "screens", "architecture", "decisions", "start", "status", "main"}
    if page.get("flow") and any(isinstance(item, dict) and not item.get("after") and not item.get("group")
                                for item in flows):
        problems.append("$.flows: this page already has a how section; set after on each flow")
    for i, flow in enumerate(flows):
        path = f"$.flows[{i}]"
        if not isinstance(flow, dict):
            problems.append(f"{path}: must be an object")
            continue
        fid = flow.get("id")
        if not isinstance(fid, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", fid):
            problems.append(f"{path}.id: a lowercase id (letters, digits, hyphens)")
        elif fid in reserved or fid in seen:
            problems.append(f"{path}.id: {fid!r} is already used")
        else:
            seen.add(fid)
        for field in ("heading", "intro", "caption"):
            if not is_bi(flow.get(field)):
                problems.append(f"{path}.{field}: needs en and zh")
        spec = flow.get("spec")
        if not isinstance(spec, dict):
            problems.append(f"{path}.spec: required")
            continue
        columns = spec.get("columns")
        if (not isinstance(columns, list) or not columns
                or any(not isinstance(col, list) or not col for col in columns)):
            problems.append(f"{path}.spec.columns: a non-empty list of non-empty columns")
            columns = []
        if "sinks" in spec and not isinstance(spec.get("sinks"), list):
            problems.append(f"{path}.spec.sinks: a list of step indexes")
            sinks = []
        else:
            sinks = spec.get("sinks") or []
        steps = flow.get("steps")
        if not isinstance(steps, list) or not steps:
            problems.append(f"{path}.steps: at least one step")
            steps = []
        placed: list[int] = []
        bad_index = False
        for column in columns:
            for step in column:
                if not _index(step):
                    bad_index = True
                else:
                    placed.append(step)
        for step in sinks:
            if not _index(step):
                bad_index = True
            else:
                placed.append(step)
        if bad_index:
            problems.append(f"{path}.spec: step indexes must be integers")
        elif steps and sorted(placed) != list(range(len(steps))):
            problems.append(f"{path}.spec: each step index must be placed exactly once (columns plus sinks)")
        column_steps = [step for column in columns for step in column if _index(step)]
        if not _index(spec.get("core")) or spec.get("core") not in column_steps:
            problems.append(f"{path}.spec.core: must be a step that sits in a column")
        for s, step in enumerate(steps):
            sp = f"{path}.steps[{s}]"
            if not isinstance(step, dict):
                problems.append(f"{sp}: must be an object")
                continue
            if not is_bi(step.get("title")) or not is_bi(step.get("note")):
                problems.append(f"{sp}: title and note need en and zh")
            if step.get("tone") not in FLOW_TONES:
                problems.append(f"{sp}.tone: one of {', '.join(sorted(FLOW_TONES))}")
            if step.get("icon") not in FLOW_ICONS:
                problems.append(f"{sp}.icon: unknown icon")
        ticks = flow.get("ticks")
        if not isinstance(ticks, list) or not 1 <= len(ticks) <= 4:
            problems.append(f"{path}.ticks: 1 to 4 lines")
        else:
            for t, tick in enumerate(ticks):
                if not is_bi(tick):
                    problems.append(f"{path}.ticks[{t}]: needs en and zh")
        if "lanes" in spec and (
            not isinstance(spec.get("lanes"), list)
            or any(not isinstance(name, str) or not name.strip() for name in spec["lanes"])
        ):
            problems.append(f"{path}.spec.lanes: a list of names")
            lanes: list = []
        else:
            lanes = spec.get("lanes") or []
        if "selectedLane" in spec:
            sel = spec.get("selectedLane")
            if not _index(sel) or not lanes or sel < 0 or sel >= len(lanes):
                problems.append(f"{path}.spec.selectedLane: out of range")
        groups = len(columns) + (1 if lanes else 0)
        if "boundaryAfter" in spec and spec.get("boundaryAfter") is not None:
            boundary = spec.get("boundaryAfter")
            if not _index(boundary) or groups < 2 or boundary < 0 or boundary >= groups - 1:
                problems.append(f"{path}.spec.boundaryAfter: a column that still has a column after it")
            zones = flow.get("zones")
            en_z = zones.get("en") if isinstance(zones, dict) else None
            zh_z = zones.get("zh") if isinstance(zones, dict) else None
            if not isinstance(en_z, list) or not isinstance(zh_z, list) or len(en_z) != 3 or len(zh_z) != 3:
                problems.append(f"{path}.zones: en and zh lists of three labels (inside, boundary, outside)")
            else:
                for lang in ("en", "zh"):
                    labels = zones[lang]
                    if any(not isinstance(label, str) or not label.strip() for label in labels):
                        problems.append(f"{path}.zones.{lang}: three non-empty labels")
        elif flow.get("zones"):
            problems.append(f"{path}.zones: set boundaryAfter, or remove zones")
        if "loop" in spec and not isinstance(spec.get("loop"), bool):
            problems.append(f"{path}.spec.loop: true or false")
        elif spec.get("loop") and len(columns) < 2:
            problems.append(f"{path}.spec.loop: needs at least two columns")
        if "meter" in spec and not isinstance(spec.get("meter"), bool):
            problems.append(f"{path}.spec.meter: true or false")
        if flow.get("after") is not None:
            after = flow.get("after")
            if not isinstance(after, str) or not _section_exists(page, after):
                problems.append(f"{path}.after: unknown section id {after!r}")
        if flow.get("group") is not None:
            group = flow.get("group")
            group_ids = {g.get("id") for g in page.get("groups") or [] if isinstance(g, dict)}
            if not isinstance(group, str) or group not in group_ids:
                problems.append(f"{path}.group: unknown project group {group!r} (hub only)")
            elif flow.get("after") is not None:
                problems.append(f"{path}: set after or group, not both")
    return problems


# ----------------------------------------------------------------------------
# html helpers
# ----------------------------------------------------------------------------

def inline(text: str) -> str:
    """Escape text but keep a tiny inline subset: em, strong, code, br, a[href]."""
    out = html.escape(text, quote=True)
    out = INLINE_TAG.sub(lambda m: f"<{m.group(1)}{m.group(2)}>", out)
    # a short command or name in running text stays on one line ("claude --resume")
    out = SHORT_CODE.sub(lambda m: f'<code class="nowrap">{m.group(1)}</code>'
                         if len(html.unescape(m.group(1))) <= 28 else m.group(0), out)
    out = INLINE_LINK.sub(lambda m: f'<a href="{m.group(1)}">', out)
    return out.replace("&lt;/a&gt;", "</a>")


def attr(text: str) -> str:
    return html.escape(re.sub(r"<[^>]+>", "", text), quote=True)


def is_bi(value) -> bool:
    return isinstance(value, dict) and "en" in value and "zh" in value


def bi(value, tag="span", cls="", extra=""):
    """Render a bilingual pair (or a single language-neutral string)."""
    if value is None:
        return ""
    if is_bi(value):
        en_cls = f"lang-en {cls}".strip()
        zh_cls = f"lang-zh {cls}".strip()
        return (f'<{tag} class="{en_cls}"{extra}>{inline(value["en"])}</{tag}>'
                f'<{tag} class="{zh_cls}" lang="zh-Hant"{extra}>{inline(value["zh"])}</{tag}>')
    cls_attr = f' class="{cls}"' if cls else ""
    return f"<{tag}{cls_attr}{extra}>{inline(str(value))}</{tag}>"


def text_of(value, lang="en") -> str:
    if is_bi(value):
        return re.sub(r"<[^>]+>", "", value[lang])
    return re.sub(r"<[^>]+>", "", str(value))


def href(url: str) -> str:
    return html.escape(url, quote=True)


GITHUB_SVG = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 .7a11.5 11.5 0 0 0-3.64 22.4c.58.1.79-.25.79-.56v-2.24c-3.22.7-3.9-1.37-3.9-1.37-.52-1.34-1.28-1.7-1.28-1.7-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36 .96 .1-.75.4-1.26.73-1.55-2.57-.29-5.28-1.29-5.28-5.69 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.16 1.18a10.96 10.96 0 0 1 5.76 0c2.2-1.49 3.16-1.18 3.16-1.18.63 1.59.23 2.76.11 3.05 .74 .81 1.19 1.83 1.19 3.09 0 4.42-2.72 5.39-5.3 5.68 .42 .36.79 1.07.79 2.16v3.21c0 .31.21 .67 .8.56A11.5 11.5 0 0 0 12 .7Z"/></svg>')

DEFAULT_NAV = {
    "flow": {"en": "How it works", "zh": "運作方式"},
    "capabilities": {"en": "Features", "zh": "功能"},
    "showcase": {"en": "Screens", "zh": "畫面"},
    "architecture": {"en": "Architecture", "zh": "架構"},
    "decisions": {"en": "Decisions", "zh": "設計取捨"},
    "quickstart": {"en": "Get started", "zh": "開始使用"},
    "status": {"en": "Status", "zh": "目前狀態"},
}
SECTION_IDS = {
    "flow": "how", "capabilities": "features", "showcase": "screens",
    "architecture": "architecture", "decisions": "decisions",
    "quickstart": "start", "status": "status",
}


def palette_of(page: dict) -> dict:
    pal = page.get("palette", "lime")
    if isinstance(pal, str):
        if pal not in PALETTES:
            raise PageError(f"unknown palette {pal!r}; choose one of {sorted(PALETTES)} or give a custom object")
        return dict(PALETTES[pal])
    base = dict(PALETTES[pal.get("base", "lime")])
    base.update({k: v for k, v in pal.items() if k != "base"})
    return base


def logo_svg(mark: str, pal: dict, size: int) -> str:
    font = {1: 0.54, 2: 0.42, 3: 0.32}[len(mark)] * size
    r = size * 0.27
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">'
        f'<rect width="{size}" height="{size}" rx="{r:.1f}" fill="{pal["ink"]}"/>'
        f'<text x="50%" y="53%" text-anchor="middle" dominant-baseline="middle" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="{font:.1f}" '
        f'font-weight="800" fill="{pal["accent"]}">{html.escape(mark)}</text>'
        f'<circle cx="{size*0.79:.1f}" cy="{size*0.21:.1f}" r="{size*0.085:.1f}" fill="{pal["signal"]}"/>'
        f"</svg>\n"
    )


# ----------------------------------------------------------------------------
# visual blocks
# ----------------------------------------------------------------------------

def panel_top(visual: dict) -> str:
    top = bi(visual.get("top", ""))
    badge = visual.get("badge")
    badge_html = f'<span class="live-dot">{bi(badge)}</span>' if badge else '<span class="dots"><i></i><i></i><i></i></span>'
    return f'<div class="panel-top"><span>{top}</span>{badge_html}</div>'


def render_visual(visual: dict, assets: dict) -> str:
    vtype = visual["type"]
    if vtype == "image":
        src = assets[visual["src"]]
        cap = visual.get("caption")
        cap_html = f"<figcaption>{bi(cap)}</figcaption>" if cap else ""
        return (f'<div class="visual-wrap is-image"><figure class="shot">'
                f'<img src="{href(src)}" alt="{attr(text_of(visual["alt"]))}" loading="eager">{cap_html}</figure></div>')

    if vtype == "receipt":
        rows = []
        for row in visual.get("rows", []):
            state = row.get("state", "ok")
            glyph = {"ok": "&#10003;", "wait": "&#8230;", "warn": "!", "fail": "&#215;"}[state]
            rows.append(
                f'<div class="check-row"><span class="check-mark is-{state}">{glyph}</span>'
                f'<span>{bi(row["label"], "strong")}'
                + (f'<small>{inline(row["detail"])}</small>' if row.get("detail") else "")
                + "</span>"
                + (f'<span class="check-side">{inline(row["side"])}</span>' if row.get("side") else "<span></span>")
                + "</div>"
            )
        foot = visual.get("footer")
        foot_html = (f'<div class="panel-footer"><span>{bi(foot.get("left", ""))}</span>'
                     f'<span>{bi(foot.get("right", ""))}</span></div>') if foot else ""
        meta = visual.get("meta")
        return (f'<div class="visual-wrap"><div class="panel">{panel_top(visual)}<div class="panel-body">'
                + (f'<div class="panel-name">{inline(visual["name"])}</div>' if visual.get("name") else "")
                + (f'<div class="panel-meta">{bi(meta)}</div>' if meta else "")
                + f'<div class="check-list">{"".join(rows)}</div>{foot_html}</div></div></div>')

    if vtype == "terminal":
        lines = []
        for line in visual.get("lines", []):
            kind = line.get("kind", "out")
            lines.append(bi(line["text"], "span", f"t-{kind}"))
        return (f'<div class="visual-wrap"><div class="panel">{panel_top(visual)}'
                f'<pre class="term">{"".join(lines)}</pre></div></div>')

    if vtype == "report":
        rows = []
        for row in visual.get("rows", []):
            level = row.get("level", "info")
            rows.append(
                f'<div class="report-row"><span>{bi(row["title"], "strong")}'
                + (f'<small>{inline(row["meta"])}</small>' if row.get("meta") else "")
                + f'</span><span class="pill pill-{level}">{bi(row["label"])}</span></div>'
            )
        foot = visual.get("footer")
        foot_html = (f'<div class="panel-footer"><span>{bi(foot.get("left", ""))}</span>'
                     f'<span>{bi(foot.get("right", ""))}</span></div>') if foot else ""
        return (f'<div class="visual-wrap"><div class="panel is-light">{panel_top(visual)}<div class="panel-body">'
                f'{bi(visual.get("title", ""), "div", "report-title")}'
                + (f'<div class="panel-meta">{bi(visual["meta"])}</div>' if visual.get("meta") else "")
                + f'{"".join(rows)}{foot_html}</div></div></div>')

    if vtype == "chat":
        msgs = []
        for msg in visual.get("messages", []):
            role = msg.get("role", "ai")
            name = f'<small>{inline(msg["name"])}</small>' if msg.get("name") else ""
            cite = f'<span class="cite">{inline(msg["cite"])}</span>' if msg.get("cite") else ""
            msgs.append(f'<div class="bubble bubble-{role}">{name}{bi(msg["text"])}{cite}</div>')
        return (f'<div class="visual-wrap"><div class="panel">{panel_top(visual)}'
                f'<div class="chat">{"".join(msgs)}</div></div></div>')

    if vtype == "stack":
        cards = []
        for item in visual.get("items", []):
            status = f'<span class="stack-status">{bi(item["status"])}</span>' if item.get("status") else "<span></span>"
            cards.append(
                f'<div class="stack-card"><span class="stack-icon">{inline(item.get("icon", "•"))}</span>'
                f'<span><strong>{inline(item["name"])}</strong>'
                + (f'<small>{bi(item["detail"])}</small>' if item.get("detail") else "")
                + f"</span>{status}</div>"
            )
        return (f'<div class="visual-wrap"><div class="panel">{panel_top(visual)}'
                f'<div class="stack">{"".join(cards)}</div></div></div>')

    raise PageError(f"unknown visual type {vtype!r}")


# ----------------------------------------------------------------------------
# sections
# ----------------------------------------------------------------------------

def heading(sec: dict, extra_class="") -> str:
    kicker = f'<div class="section-kicker">{bi(sec["kicker"])}</div>' if sec.get("kicker") else ""
    intro = bi(sec["intro"], "p") if sec.get("intro") else ""
    return (f'<div class="section-heading {extra_class}"><div>{kicker}{bi(sec["title"], "h2")}</div>'
            f"{intro}</div>")


def anchor(link: dict, cls: str = "") -> str:
    """A link from page.json; an {"en", "zh"} href gives each language its own anchor."""
    if not is_bi(link["href"]):
        cls_attr = f' class="{cls}"' if cls else ""
        return f'<a{cls_attr} href="{href(link["href"])}">{bi(link["label"])}</a>'
    label = link["label"] if is_bi(link["label"]) else {"en": link["label"], "zh": link["label"]}
    c = f" {cls}" if cls else ""
    return (f'<a class="lang-en{c}" href="{href(link["href"]["en"])}">{inline(label["en"])}</a>'
            f'<a class="lang-zh{c}" lang="zh-Hant" href="{href(link["href"]["zh"])}">{inline(label["zh"])}</a>')


def button(link: dict, cls: str) -> str:
    return anchor(link, f"button {cls}")


def flow_payload(spec: dict) -> dict:
    payload = {"columns": spec["columns"], "core": spec["core"]}
    if spec.get("sinks"):
        payload["sinks"] = spec["sinks"]
    if spec.get("lanes"):
        payload["lanes"] = spec["lanes"]
    if spec.get("selectedLane") is not None:
        payload["selectedLane"] = spec["selectedLane"]
    if spec.get("meter"):
        payload["meter"] = True
    if spec.get("boundaryAfter") is not None:
        payload["boundaryAfter"] = spec["boundaryAfter"]
    if spec.get("loop"):
        payload["loop"] = True
    return payload


def render_flow_figure(flow: dict, lang: str) -> str:
    """One language. The other language is a second figure, hidden by the page."""
    spec = flow["spec"]
    data = html.escape(
        json.dumps(flow_payload(spec), ensure_ascii=False, separators=(",", ":")),
        quote=True,
    )
    order = [step for column in spec["columns"] for step in column]
    order += list(spec.get("sinks") or [])
    items = []
    for position, index in enumerate(order):
        step = flow["steps"][index]
        link = '<span class="fd-link" aria-hidden="true"></span>' if position < len(order) - 1 else ""
        items.append(
            f'<li class="fd-node" data-step="{index}" data-tone="{html.escape(step["tone"], quote=True)}"'
            f' data-icon="{html.escape(step["icon"], quote=True)}">'
            f'<span class="fd-head"><span class="fd-chip"></span>'
            f'<span class="fd-step" aria-hidden="true">{position + 1:02d}</span></span>'
            f'<p class="fd-title">{inline(step["title"][lang])}</p>'
            f'<p class="fd-note">{inline(step["note"][lang])}</p>{link}</li>'
        )
    ticks = "".join(f"<li>{inline(tick[lang])}</li>" for tick in flow["ticks"])
    zones = ""
    if spec.get("boundaryAfter") is not None and flow.get("zones"):
        zones = "<ul class=\"fd-zones\">" + "".join(
            f"<li>{inline(label)}</li>" for label in flow["zones"][lang]
        ) + "</ul>"
    lang_cls = "lang-en" if lang == "en" else "lang-zh"
    lang_attr = "" if lang == "en" else ' lang="zh-Hant"'
    return (
        f'<figure class="fd {lang_cls}"{lang_attr} data-fd="{data}">'
        f'<ol class="fd-legend">{"".join(items)}</ol>'
        f'<ul class="fd-ticks">{ticks}</ul>{zones}'
        f"<figcaption>{inline(flow['caption'][lang])}</figcaption></figure>"
    )


def render_flow_section(flow: dict) -> str:
    return (
        f'<section class="section" id="{html.escape(flow["id"])}">'
        f'{heading({"title": flow["heading"], "intro": flow["intro"]})}'
        f'{render_flow_figure(flow, "en")}{render_flow_figure(flow, "zh")}</section>'
    )


def render_default_flow_section(flows: list) -> str:
    stories = []
    for flow in flows:
        stories.append(
            f'<div class="fd-story" id="{html.escape(flow["id"])}">'
            f'{bi(flow["heading"], "h3")}{bi(flow["intro"], "p")}'
            f'{render_flow_figure(flow, "en")}{render_flow_figure(flow, "zh")}</div>'
        )
    head = heading({"title": {"en": "How it works", "zh": "運作方式"}})
    return f'<section class="section" id="how">{head}{"".join(stories)}</section>'


def place_flows(parts: list, page: dict) -> list:
    """Insert flow sections. Pages without flows get the same part list back.
    Flows with a group are drawn by the hub inside that group's band."""
    flows = [flow for flow in page.get("flows") or [] if not flow.get("group")]
    if not flows:
        return parts

    def find(token: str):
        for index, part in enumerate(parts):
            if token in part:
                return index
        return None

    jobs = []
    default = [flow for flow in flows if not flow.get("after")]
    if default:
        first = None
        for token in (
            'class="band"', 'id="how"', 'id="features"', 'id="screens"',
            'id="architecture"', 'id="decisions"', 'id="start"', 'id="status"',
        ):
            first = find(token)
            if first is not None:
                break
        jobs.append((first if first is not None else -1, render_default_flow_section(default)))
    grouped: dict = {}
    order: list = []
    for flow in flows:
        after = flow.get("after")
        if not after:
            continue
        if after not in grouped:
            grouped[after] = []
            order.append(after)
        grouped[after].append(flow)
    for key in order:
        idx = find(f'id="{key}"')
        block = "\n".join(render_flow_section(flow) for flow in grouped[key])
        jobs.append((idx if idx is not None else len(parts) - 1, block))
    for idx, block in reversed(sorted(jobs, key=lambda job: job[0])):
        parts.insert(idx + 1, block)
    return parts


def render_page(page: dict, assets: dict) -> str:
    pal = palette_of(page)
    repo = page["repo"]
    slug = page["slug"]
    gh = f"https://github.com/{repo}"
    url = f"{SITE_ROOT}/{slug}/"
    name = page["name"]
    title_en = f'{name} · {text_of(page["title"], "en")}'
    title_zh = f'{name} · {text_of(page["title"], "zh")}'
    desc_en = text_of(page["description"], "en")
    desc_zh = text_of(page["description"], "zh")

    # navigation from present sections
    nav_items = []
    for key in ("flow", "capabilities", "showcase", "architecture", "decisions", "quickstart", "status"):
        sec = page.get(key)
        if not sec or sec.get("nav") is False:
            continue
        label = sec.get("nav") or DEFAULT_NAV[key]
        nav_items.append(f'<a href="#{SECTION_IDS[key]}">{bi(label)}</a>')
    nav_items = nav_items[:4]
    if not page.get("flow") and any(
        isinstance(item, dict) and not item.get("after") and not item.get("group")
        for item in (page.get("flows") or [])
    ):
        nav_items.insert(0, f'<a href="#how">{bi({"en": "How it works", "zh": "運作方式"})}</a>')
        nav_items = nav_items[:4]

    hero = page["hero"]
    notes = "".join(bi(n) if is_bi(n) else f"<span>{inline(n)}</span>" for n in hero.get("notes", []))
    buttons = button(hero["primary"], "button-primary")
    if hero.get("secondary"):
        buttons += button(hero["secondary"], "button-secondary")

    parts: list[str] = []

    parts.append(
        f'<section class="hero" id="top"><div class="hero-copy">'
        f'<div class="eyebrow">{bi(hero["eyebrow"])}</div>'
        f'{bi(hero["headline"], "h1")}{bi(hero["lede"], "p")}'
        f'<div class="button-row">{buttons}</div>'
        + (f'<div class="hero-notes">{notes}</div>' if notes else "")
        + f"</div>{render_visual(hero['visual'], assets)}</section>"
    )

    stats = page.get("stats") or []
    if stats:
        cells = "".join(
            f'<div class="stat"><span class="stat-value">{inline(s["value"])}</span>'
            f'<span class="stat-label">{bi(s["label"])}</span></div>'
            for s in stats
        )
        parts.append(f'<div class="stats n{len(stats)}">{cells}</div>')

    prob = page.get("problem")
    if prob:
        quote = bi(prob["quote"], "blockquote", "quote") if prob.get("quote") else ""
        parts.append(
            f'<section class="band"><div class="section problem-grid"><div>'
            f'<div class="section-kicker">{bi(prob.get("kicker", {"en": "The problem", "zh": "問題在哪裡"}))}</div>'
            f'{bi(prob["title"], "h2")}{bi(prob["body"], "p")}</div>{quote}</div></section>'
        )

    flow = page.get("flow")
    if flow:
        steps = "".join(
            f'<article class="flow-card"><div class="flow-number">{i:02d}</div>'
            f'{bi(st["title"], "h3")}{bi(st["body"], "p")}</article>'
            for i, st in enumerate(flow["steps"], 1)
        )
        parts.append(
            f'<section class="section" id="how">{heading(flow)}'
            f'<div class="flow-grid n{len(flow["steps"])}">{steps}</div></section>'
        )

    caps = page["capabilities"]
    cards = "".join(
        f'<article class="card"><div class="card-icon">{i:02d}</div>{bi(c["title"], "h3")}{bi(c["body"], "p")}'
        + (f'<span class="tag">{inline(c["tag"])}</span>' if c.get("tag") else "")
        + "</article>"
        for i, c in enumerate(caps["items"], 1)
    )
    parts.append(
        f'<section class="tinted" id="features"><div class="section">{heading(caps)}'
        f'<div class="card-grid">{cards}</div></div></section>'
    )

    show = page.get("showcase")
    if show:
        shots = "".join(
            f'<figure class="shot"><img src="{href(assets[s["src"]])}" alt="{attr(text_of(s["alt"]))}" loading="lazy">'
            + (f"<figcaption>{bi(s['caption'])}</figcaption>" if s.get("caption") else "")
            + "</figure>"
            for s in show["shots"]
        )
        parts.append(
            f'<section class="section" id="screens">{heading(show)}'
            f'<div class="showcase-grid n{len(show["shots"])}">{shots}</div></section>'
        )

    arch = page.get("architecture")
    if arch:
        nodes = []
        for i, node in enumerate(arch["nodes"]):
            if i:
                nodes.append('<div class="map-arrow" aria-hidden="true">&#8594;</div>')
            lines = "".join(bi(line) for line in node.get("lines", []))
            core = " is-core" if node.get("core") else ""
            nodes.append(f'<div class="map-node{core}">{bi(node["name"], "strong")}{lines}</div>')
        ret = f'<div class="map-return">{bi(arch["return"])}</div>' if arch.get("return") else ""
        label = f'<div class="map-label">{bi(arch["label"])}</div>' if arch.get("label") else ""
        princ = arch.get("principles")
        princ_html = ""
        if princ:
            items = "".join(bi(item, "li") for item in princ["items"])
            princ_html = f'<aside class="principles">{bi(princ["title"], "h3")}<ul class="tick-list">{items}</ul></aside>'
        solo = "" if princ else " is-solo"
        parts.append(
            f'<section class="section" id="architecture">{heading(arch)}'
            f'<div class="arch-shell{solo}"><div class="arch-map">{label}'
            f'<div class="map-flow n{len(arch["nodes"])}">{"".join(nodes)}</div>{ret}</div>{princ_html}</div></section>'
        )

    dec = page.get("decisions")
    if dec:
        items = "".join(
            f'<div class="decision"><div class="decision-num">{i:02d}</div>{bi(d["title"], "h3")}{bi(d["body"], "p")}</div>'
            for i, d in enumerate(dec["items"], 1)
        )
        parts.append(
            f'<section class="section" id="decisions">{heading(dec)}<div class="decision-list">{items}</div></section>'
        )

    qs = page.get("quickstart")
    if qs:
        qs_buttons = ""
        if qs.get("primary"):
            qs_buttons += button(qs["primary"], "button-primary")
        if qs.get("secondary"):
            qs_buttons += button(qs["secondary"], "button-secondary")
        steps = []
        for i, st in enumerate(qs["steps"], 1):
            body = bi(st["body"], "p") if st.get("body") else ""
            code = ""
            if st.get("code"):
                cid = f"code-{i}"
                code = (f'<div class="code-wrap"><pre class="code" id="{cid}">{html.escape(st["code"])}</pre>'
                        f'<button class="copy" type="button" data-copy="{cid}">'
                        f'<span class="idle">{bi({"en": "Copy", "zh": "複製"})}</span>'
                        f'<span class="done">{bi({"en": "Copied", "zh": "已複製"})}</span></button></div>')
            steps.append(f'<article class="step">{bi(st["title"], "h3")}{body}{code}</article>')
        kicker = f'<div class="section-kicker">{bi(qs["kicker"])}</div>' if qs.get("kicker") else ""
        parts.append(
            f'<section class="dark-band" id="start"><div class="section qs-grid"><div>{kicker}'
            f'{bi(qs["title"], "h2")}{bi(qs["intro"], "p") if qs.get("intro") else ""}'
            + (f'<div class="button-row">{qs_buttons}</div>' if qs_buttons else "")
            + f'</div><div class="steps">{"".join(steps)}</div></div></section>'
        )

    status = page["status"]
    works = "".join(bi(x, "li") for x in status.get("works", []))
    limits = "".join(bi(x, "li") for x in status.get("limits", []))
    facts = "".join(
        f'<div class="fact"><dt>{bi(f["label"])}</dt><dd>{bi(f["value"])}</dd></div>'
        for f in page["facts"]
    )
    works_title = status.get("works_title", {"en": "Works today", "zh": "目前可用"})
    limits_title = status.get("limits_title", {"en": "Limits and not yet", "zh": "限制與尚未完成"})
    parts.append(
        f'<section class="section" id="status">{heading(status)}<div class="status-grid">'
        f'<div class="status-col">{bi(works_title, "h3")}<ul>{works}</ul></div>'
        f'<div class="status-col is-limits">{bi(limits_title, "h3")}<ul>{limits}</ul></div></div>'
        f'<dl class="facts">{facts}</dl></section>'
    )

    parts.append(
        '<section class="more"><div class="more-inner">'
        + bi({
            "en": "<strong>More from Ted Huang.</strong> Every public project has a page like this one, in English and Traditional Chinese.",
            "zh": "<strong>Ted Huang 的其他作品。</strong>每個公開專案都有一頁像這樣的中英雙語介紹。",
        }, "p")
        + f'<a class="button button-secondary" href="{HUB}">{bi({"en": "All projects →", "zh": "全部專案 →"})}</a>'
        + "</div></section>"
    )

    # footer links
    links = [f'<a href="{href(gh)}">GitHub</a>']
    for link in page.get("links", []):
        links.append(anchor(link))
    lic = page.get("license") or {}
    if lic.get("href"):
        lic_href = lic["href"] if lic["href"].startswith("http") else f'{gh}/blob/{page.get("default_branch", "main")}/{lic["href"]}'
        links.append(f'<a href="{href(lic_href)}">{bi(lic.get("label", {"en": "License", "zh": "授權"}))}</a>')
    links.append('<a href="https://www.ted-h.com">ted-h.com</a>')

    tagline = page.get("footer_tagline", page["title"])

    head_ld = {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": name,
        "codeRepository": gh,
        "description": desc_en,
        "author": {"@type": "Person", "name": "Ted Huang", "url": "https://www.ted-h.com"},
        "url": url,
    }
    if page.get("language"):
        head_ld["programmingLanguage"] = page["language"]
    if lic.get("spdx"):
        head_ld["license"] = f"https://spdx.org/licenses/{lic['spdx']}.html"

    flow_head = ""
    if page.get("flows"):
        flow_head = '<link rel="stylesheet" href="flow.css">\n<script src="flow.js" defer></script>\n'
    nav_html = "".join(nav_items)
    parts = place_flows(parts, page)
    body = "\n".join(parts)
    return f"""<!doctype html>
<!-- Generated from site/page.json by the project-page kit (https://github.com/teddashh/teddashh.github.io/tree/main/kit). Edit page.json, then re-render. -->
<html lang="en" data-lang="en" data-title-en="{attr(title_en)}" data-title-zh="{attr(title_zh)}" data-desc-en="{attr(desc_en)}" data-desc-zh="{attr(desc_zh)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'none'; base-uri 'none'; form-action 'none'">
<meta name="theme-color" content="{pal['ink']}">
<title>{html.escape(title_en)}</title>
<meta name="description" content="{attr(desc_en)}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="en" href="{url}">
<link rel="alternate" hreflang="zh-Hant" href="{url}?lang=zh-TW">
<link rel="alternate" hreflang="x-default" href="{url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{attr(title_en)}">
<meta property="og:description" content="{attr(desc_en)}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="styles.css">
<script src="lang.js"></script>
<script src="app.js" defer></script>
{flow_head}<script type="application/ld+json">{json.dumps(head_ld, ensure_ascii=False)}</script>
</head>
<body>
<a class="skip-link" href="#main">{bi({"en": "Skip to content", "zh": "跳到主要內容"})}</a>
<header class="site-header"><div class="header-inner">
<a class="brand" href="#top"><img src="logo.svg" alt="" width="36" height="36"><span>{html.escape(name)}</span></a>
<button class="menu-button" type="button" aria-expanded="false" aria-controls="site-navigation">{bi({"en": "Menu", "zh": "選單"})}</button>
<nav class="site-nav" id="site-navigation" aria-label="Primary">
{nav_html}
<div class="language-switch" role="group" aria-label="Language / 語言"><button type="button" data-language="en" aria-pressed="true">EN</button><button type="button" data-language="zh" aria-pressed="false">繁中</button></div>
<a class="github-link" href="{href(gh)}">{GITHUB_SVG}<span>GitHub</span></a>
</nav>
</div></header>
<main id="main">
{body}
</main>
<footer class="site-footer"><div class="footer-inner">
<div><div class="footer-brand"><img src="logo.svg" alt="" width="32" height="32"><span>{html.escape(name)}</span></div>
{bi(tagline, "p")}
<p>{bi({"en": "Built by", "zh": "作者"})} <a href="https://github.com/{OWNER}">Ted Huang</a> · © <span data-year>2026</span></p></div>
<div class="footer-links">{"".join(links)}</div>
</div></footer>
</body>
</html>
"""


def render_404(page: dict) -> str:
    name = page["name"]
    return f"""<!doctype html>
<html lang="en" data-lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; script-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'">
<meta name="robots" content="noindex">
<title>{html.escape(name)} · 404</title>
<link rel="icon" href="/{page['slug']}/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/{page['slug']}/styles.css">
<script src="/{page['slug']}/lang.js"></script>
</head>
<body>
<main class="notfound">
<div class="eyebrow">404</div>
{bi({"en": "This page does not exist.", "zh": "找不到這個頁面。"}, "h2")}
<p><a class="button button-primary" href="/{page['slug']}/">{bi({"en": f"Back to {name}", "zh": f"回到 {name}"})}</a></p>
</main>
</body>
</html>
"""


PAGES_WORKFLOW = """name: Deploy project page to GitHub Pages

on:
  push:
    branches: [{branch}]
    paths:
      - "site/**"
      - ".github/workflows/pages.yml"{extra_paths}
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  deploy:
    name: Deploy static site
    runs-on: ubuntu-latest
    timeout-minutes: 10
    environment:
      name: github-pages
      url: ${{{{ steps.deployment.outputs.page_url }}}}
    steps:
      - name: Check out repository
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
{extra_steps}
      - name: Configure GitHub Pages
        uses: actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d # v6.0.0

      - name: Upload site artifact
        uses: actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0
        with:
          path: {artifact}

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346 # v5.0.1
"""


def workflow_for(page: dict) -> str:
    extra = page.get("pages_extra") or {}
    extra_paths = "".join(f'\n      - "{p}"' for p in extra.get("paths", []))
    extra_steps = ""
    artifact = "./site"
    if extra.get("copy"):
        lines = ["", "      - name: Assemble site", "        run: |", "          mkdir -p _site", "          cp -R site/. _site/"]
        for src, dst in extra["copy"]:
            lines.append(f'          mkdir -p "_site/{Path(dst).parent.as_posix()}"')
            lines.append(f'          cp "{src}" "_site/{dst}"')
        extra_steps = "\n".join(lines) + "\n"
        artifact = "./_site"
    return PAGES_WORKFLOW.format(
        branch=page.get("default_branch", "main"),
        extra_paths=extra_paths,
        extra_steps=extra_steps,
        artifact=artifact,
    )


def collect_assets(page: dict, repo_dir: Path) -> dict:
    """Map repo-relative image paths to site-relative paths, copying as needed."""
    sources = []
    visual = page["hero"].get("visual", {})
    if visual.get("type") == "image":
        sources.append(visual["src"])
    for shot in (page.get("showcase") or {}).get("shots", []):
        sources.append(shot["src"])
    mapping = {}
    for src in sources:
        if src.startswith("site/"):
            mapping[src] = src[len("site/"):]
            if not (repo_dir / src).is_file():
                raise PageError(f"image not found: {src}")
            continue
        path = repo_dir / src
        if not path.is_file():
            raise PageError(f"image not found: {src}")
        mapping[src] = f"assets/{path.name}"
    return mapping


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    repo_dir = Path(argv[1]).resolve()
    check_only = "--check" in argv
    src = repo_dir / "site" / "page.json"
    page = json.loads(src.read_text(encoding="utf-8"))
    problems = validate(page)
    if problems:
        print(f"{src}: {len(problems)} problem(s)")
        for p in problems:
            print("  -", p)
        return 1
    assets = collect_assets(page, repo_dir)
    html_out = render_page(page, assets)
    if check_only:
        print(f"{src}: ok (check only)")
        return 0

    site = repo_dir / "site"
    site.mkdir(exist_ok=True)
    pal = palette_of(page)
    theme = ":root {\n" + "".join(
        f"  --{k.replace('accent2', 'accent-2')}: {v};\n" for k, v in pal.items()
    ) + "}\n\n"
    css = theme + (KIT / "base.css").read_text(encoding="utf-8")
    if page.get("flows"):
        css += flow_map(pal)
    (site / "styles.css").write_text(css, encoding="utf-8")
    shutil.copyfile(KIT / "lang.js", site / "lang.js")
    shutil.copyfile(KIT / "app.js", site / "app.js")
    if page.get("flows"):
        shutil.copyfile(KIT / "flow.js", site / "flow.js")
        shutil.copyfile(KIT / "flow.css", site / "flow.css")
    else:
        for extra in ("flow.js", "flow.css"):
            stale = site / extra
            if stale.is_file():
                stale.unlink()
    (site / "index.html").write_text(html_out, encoding="utf-8")
    (site / "404.html").write_text(render_404(page), encoding="utf-8")
    (site / "logo.svg").write_text(logo_svg(page["mark"], pal, 48), encoding="utf-8")
    (site / "favicon.svg").write_text(logo_svg(page["mark"], pal, 64), encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")
    url = f"{SITE_ROOT}/{page['slug']}/"
    (site / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {url}sitemap.xml\n", encoding="utf-8")
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{url}</loc>" + (f"<lastmod>{page['verified']}</lastmod>" if page.get("verified") else "") + "</url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )
    for src_rel, dst_rel in assets.items():
        if src_rel.startswith("site/"):
            continue
        dst = site / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_dir / src_rel, dst)

    wf = repo_dir / ".github" / "workflows" / "pages.yml"
    if not wf.exists() or page.get("pages_workflow") == "overwrite":
        wf.parent.mkdir(parents=True, exist_ok=True)
        wf.write_text(workflow_for(page), encoding="utf-8")
    print(f"rendered {site}/index.html ({len(html_out):,} bytes)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except PageError as exc:
        print(f"error: {exc}")
        sys.exit(1)
