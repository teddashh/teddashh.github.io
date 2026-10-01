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
`report`, `chat`, or `stack`. Capability cards come in threes or sixes; flows
have two to four steps; stats two to four items. A worked example lives at
[`openclaw-hermes-watcher/site/page.json`](https://github.com/teddashh/openclaw-hermes-watcher/blob/main/site/page.json).

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
