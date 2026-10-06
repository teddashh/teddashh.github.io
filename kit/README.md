# Project page kit

The generator behind every project page on `teddashh.github.io`. One JSON file
per repository becomes a bilingual (English / Traditional Chinese) static page
with a language switch, a strict Content Security Policy, and no third-party
requests. Standard-library Python; no build step on the reader's side.

## Files

| file | purpose |
|---|---|
| `render.py` | reads `<repo>/site/page.json`, validates it, writes the page into `<repo>/site/` and a Pages workflow into `<repo>/.github/workflows/pages.yml` (only if absent) |
| `render_hub.py` | renders the directory page of this repository from `hub.json` |
| `render_profile.py` | writes the project list of the GitHub profile README (English and Chinese) from the same `hub.json`, plus a directory under `projects/` |
| `base.css` | shared styles; each page prepends its own color variables |
| `hub.css` | extra styles for the directory page |
| `lang.js` | picks the language before first paint: `?lang=`, then the saved choice, then the browser language |
| `app.js` | language switch, menu, copy buttons, and word-boundary line breaks for Chinese headings |
| `flow.js` | animated flow diagrams. Copied into a project `site/` only when `page.json` has `flows`, and into this repository's `site/` only when `hub.json` has `flows` |
| `flow.css` | styles for those diagrams. Same copy rule as `flow.js` |
| `flow.test.js` | layout and status-line tests (`node --test kit/flow.test.js`) |
| `flow-demo.html` | local demo of every layout and palette. Not linked from the hub |
| `shoot.py` | headless Chromium screenshots (English and Chinese, desktop and mobile) for a visual check |
| `zh_breaks.py` | prints where each Chinese `h1`, `h2` and quote wraps at desktop and phone width, as text |

## Use

```bash
python3 kit/render.py path/to/repo            # validate and write path/to/repo/site/
python3 kit/render.py path/to/repo --check    # validate only
python3 kit/shoot.py  path/to/repo short-name # screenshots into ./_shots/ or $PAGE_KIT_SHOTS
python3 kit/zh_breaks.py path/to/repo         # Chinese heading line breaks, e.g. "一張表單， / 幾輪討論"
python3 kit/render_hub.py .                   # this repository's directory page
python3 kit/render_profile.py path/to/profile          # profile README project list
python3 kit/render_profile.py path/to/profile --check  # exit 1 if the profile is out of date
```

The profile renderer only replaces the block between `<!-- projects:start -->`
and `<!-- projects:end -->` in each README; everything else stays hand-written.

Commit the generated `site/` together with `page.json`. The workflow deploys
`site/` whenever it changes; enable GitHub Pages with the "GitHub Actions"
source once per repository.

## page.json

Bilingual values are `{"en": "...", "zh": "..."}`; a plain string is
language-neutral (names, versions, commands). Text may use `<em>`, `<strong>`,
`<code>`, `<br>` and `<a href="https://...">`; everything else is escaped.

Required: `repo`, `slug` (the exact repository name), `name`, `mark` (1 to 3
characters for the logo tile), `title`, `description`, `hero`, `capabilities`,
`status`, `facts`.

Optional: `palette` (`lime violet teal amber rose blue graphite ember moss`, or
an object with `base` plus overrides), `default_branch`, `verified`, `language`,
`license`, `stats`, `problem`, `flow`, `showcase`, `architecture`, `decisions`,
`quickstart`, `links`, `pages_extra` (publish extra repository files next to
`site/`).

A link (`hero.primary`, `hero.secondary`, `quickstart.primary`, `links`) is
`{"href": "...", "label": ...}`. When the target differs by language, `href`
can be bilingual too, for example `{"en": "./play/", "zh": "./play/?lang=zh"}`;
the page then shows each language its own link. Hub and profile links in
`hub.json` accept the same form.

The hero visual is one of `image` (a real screenshot), `terminal`, `receipt`,
`report`, `chat`, or `stack`. Capability cards come in threes or sixes; the
short `flow` list has two to four steps; stats two to four items. Animated
diagrams are the separate `flows` list below. A worked example lives at
[`openclaw-hermes-watcher/site/page.json`](https://github.com/teddashh/openclaw-hermes-watcher/blob/main/site/page.json).

## Animated flow diagrams (`flows`)

Optional. A page that omits `flows` renders the same HTML and CSS as before,
and does not receive `flow.js` or `flow.css`. `hub.json` may carry the same
list. `render_hub.py` checks it with these rules, appends the same `--fd-*`
mapping, and copies the two files only when the list is present. A hub
without `flows` renders the same files as before. Each item is one diagram,
in both languages. The page renders one `<figure class="fd">` per language
and hides the inactive one with the existing language switch.

```json
{
  "id": "route",
  "heading": {"en": "How a request moves", "zh": "一個請求怎麼走"},
  "intro": {"en": "In, through the core, then out.", "zh": "進來，經過核心，再出去。"},
  "spec": {"columns": [[0], [1]], "core": 1},
  "steps": [
    {"title": {"en": "Ask", "zh": "提出問題"}, "note": {"en": "A person types one question.", "zh": "有人輸入一個問題。"}, "tone": "neutral", "icon": "chat"},
    {"title": {"en": "Route", "zh": "決定路線"}, "note": {"en": "The core picks where it goes.", "zh": "核心決定要往哪裡去。"}, "tone": "accent", "icon": "route"}
  ],
  "ticks": [
    {"en": "question received", "zh": "已收到問題"},
    {"en": "lane chosen", "zh": "已選定路線"}
  ],
  "caption": {"en": "The question goes in. The core sends it on.", "zh": "問題進來，核心再把它送出去。"}
}
```

`id` is lowercase letters, digits, and hyphens, and must not reuse `top`,
`how`, `features`, `screens`, `architecture`, `decisions`, `start`, `status`,
or `main`.

`spec.columns` is a list of columns. A column with several step indexes fans
in or out. `spec.core` is a step that sits in a column: that box is wider,
with a dotted halo and a pulse at its top right corner. Every step index from
`0` through `steps.length - 1` appears exactly once, in `columns` plus
`sinks`.

Optional spec fields:

- `sinks`: step indexes drawn under the core.
- `lanes`: a final column of pills (plain names). `selectedLane` is the
  selected pill, `0` through `lanes.length - 1`.
- `meter`: `true` draws a capacity bar on the core.
- `boundaryAfter`: a column index that still has a column or a lanes group
  after it. A dashed line is drawn there. `zones` is then required:
  `{"en": ["inside", "boundary", "outside"], "zh": ["你這一側", "信任界線", "外部"]}`.
- `loop`: `true` draws a return rail under the boxes, from the last column
  back to the first. Needs at least two columns.

`steps` items need bilingual `title` and `note`, a `tone` of `neutral`,
`accent`, `warn`, or `info`, and an `icon`. Icons: `chat`, `route`, `spark`,
`shield`, `mask`, `cloud`, `check`, `ledger`, `search`, `people`, `pool`,
`clock`, `forward`, `window`, `database`, `hub`, `wallet`, `code`,
`terminal`, `user`, `gear`, `lock`, `doc`, `bolt`, `globe`, `eye`, `key`,
`upload`, `download`, `bell`, `image`, `music`, `game`.

`ticks` is 1 to 4 bilingual status lines. The engine shows one at a time:
the current line fades fully out before the next fades in. With
`prefers-reduced-motion`, the first line stays put and nothing moves.

`after` is an existing section id (`top`, `how` when the short `flow` list
is present, `features`, `screens`, `architecture`, `decisions`, `start`,
`status`, and `about` when that section is in the file, as on the hub).
The diagram is inserted immediately after that section. Without
`after`, every such diagram shares a new section `id="how"` titled "How it
works" / 「運作方式」, placed after the first content block, and the nav gains
a link to it. A page that already has the short `flow` section must set
`after` on each item, because that section already uses `id="how"`.

`kit/flow-demo.html` shows a straight chain, fan-out lanes, sinks, a trust
boundary, a capacity bar, a loop, and a fan-in, in the lime, violet, ember,
and graphite palettes, plus one dark sample. Open it from the `kit/`
directory. It is not linked from the hub.

### Color contract

`flow.css` sets no theme colors. Every paint reads a custom property, with a
fallback of `currentColor` or `Canvas`, so an unmapped host still has edges
and filled boxes. The kit appends this block to `site/styles.css` only when
the page has `flows`:

```css
.fd {
  --fd-surface: var(--paper-strong);
  --fd-edge: var(--line);
  --fd-text: var(--ink);
  --fd-faint: var(--ink-faint);
  --fd-accent: var(--signal);
  --fd-accent-ink: color-mix(in srgb, var(--signal) 60%, var(--ink));
  --fd-warn: var(--kicker);
  --fd-info: color-mix(in srgb, var(--accent-2) 40%, var(--ink));
  --fd-font: inherit;
  --fd-mono: var(--mono);
}
```

`--fd-surface` is the box fill. `--fd-edge` is rails and box strokes.
`--fd-text` is titles and the caption. The caption is bold.
`--fd-faint` is notes, lane labels, and zone labels
(the kit's `--ink-faint`, about 3.6:1 on the surface, used as secondary
text). `--fd-accent` is the bright signal: core stroke, flowing dash, halo,
pulse, and the selected lane. `--fd-accent-ink` is optional and falls back
to `--fd-accent`; the kit mixes signal 60% with ink so small accent text
clears 4.5:1 on the surface. `--fd-warn` is the boundary and the warn tone
(`--kicker`). `--fd-info` is the info tone (accent-2 mixed 40% with ink, so
it also clears 4.5:1). `--fd-font` and `--fd-mono` are optional.

### Markup the engine reads

One figure, one language. `data-fd` is the spec. The legend is the readable
fallback (search engines and browsers with JavaScript off see the steps, the
status lines, the zone labels, and the caption). The script builds an
`aria-hidden` SVG above the legend. A second `TedFlow.render` on the same
figure does not add a second SVG.

```html
<figure class="fd" data-fd='{"columns":[[0],[1],[2]],"core":1}'>
  <ol class="fd-legend">
    <li class="fd-node" data-step="0" data-tone="neutral" data-icon="doc">
      <span class="fd-head"><span class="fd-chip"></span>
        <span class="fd-step" aria-hidden="true">01</span></span>
      <p class="fd-title">Write the draft</p>
      <p class="fd-note">A short note.</p>
      <span class="fd-link" aria-hidden="true"></span>
    </li>
  </ol>
  <ul class="fd-ticks"><li>draft saved</li></ul>
  <figcaption>What the diagram shows.</figcaption>
</figure>
<script src="flow.js" defer></script>
```

`flow.js` fills each empty `.fd-chip` with a 24 by 24 line icon in
`currentColor`, so the chip takes the node tone. Layout never measures
rendered text: width is estimated, and wrapping is aware of CJK, including
the rule that a line must not open with a closing mark. A figure hidden by
the language switch still lays out.

Below about 860px of the figure's own width (a container query, not the
viewport), the SVG is hidden and the legend becomes a vertical list with
connectors. Motion pauses while a figure is off screen. `forced-colors`
uses the system colors.

### Using the files outside the kit

Copy `flow.js` and `flow.css` next to the page. No build step, no
dependencies, no external fonts. Map the host's own tokens:

```css
.fd {
  --fd-surface: var(--card);
  --fd-edge: var(--border);
  --fd-text: var(--text);
  --fd-faint: var(--text-muted);
  --fd-accent: var(--brand);
  --fd-warn: var(--warning);
  --fd-info: var(--info);
}
```

The script installs `window.TedFlow.render(element)` and
`window.TedFlow.renderAll(root)`, and on a normal page it draws every
`figure.fd` at `DOMContentLoaded`.

React: keep the figure in the component, then call
`window.TedFlow.render(ref.current)` from `useEffect` after it is in the
document.

Next.js: load the script, then call `window.TedFlow.renderAll` (or `render`
on the node) after the figure mounts. `DOMContentLoaded` has often already
fired by then.

Odoo QWeb: ship the two files as assets. After the template inserts the
figure, call `TedFlow.renderAll(root)` on the inserted fragment, for the
same reason.

A bilingual host still uses one figure per language and hides the inactive
figure itself. Do not put both languages inside one figure.

Tests:

```bash
node --test kit/flow.test.js
```

They check that every step index is placed once, that boxes stay inside the
960 unit viewBox and do not overlap, that wrapping stays inside the width
budget and does not start a line on a closing mark, and that two status
lines are never visible at the same moment.

## Rules the validator enforces

- No em-dash, en-dash, or horizontal-bar characters anywhere. Use a comma, a
  colon, or a plain hyphen.
- Chinese text is Traditional Chinese as written in Taiwan; common
  Simplified-only characters are rejected.
- Every bilingual field needs both languages.
- Optional: a local, uncommitted `kit/private-terms.txt` (one term per line)
  lists words that must never reach a public page, such as private host or
  repository names. Pages that mention one fail validation.

## Writing

Plain and concrete. Every claim should be checkable in the repository:
versions, counts, and commands come from the code. Each page has an honest
status section with what works today and what does not yet.
