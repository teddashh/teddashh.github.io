# teddashh.github.io

**English** · [繁體中文](README.zh-TW.md)

The directory of Ted Huang's open-source projects, and the kit that builds every project page.

**Live:** https://teddashh.github.io/

## What is here

- `hub.json`: the project list (groups, one-line descriptions, status). Edit it, then run `python3 kit/render_hub.py .`
- `site/`: the generated directory page, deployed by `.github/workflows/pages.yml`.
- `kit/`: the page generator every project repository uses. See [kit/README.md](kit/README.md).
- The project list on the [GitHub profile](https://github.com/teddashh) comes from the same `hub.json`, through `python3 kit/render_profile.py <profile-repo>`.

## How project pages work

Each project repository keeps its own `site/page.json`. The kit turns it into a bilingual page inside that repository's `site/`, and the repository's own Pages workflow publishes it at `https://teddashh.github.io/<repo>/`. This repository hosts only the root directory page and the kit.

All pages are static, make no third-party requests, and remember the reader's language choice across projects (same origin, one saved setting).

## License

MIT. See [LICENSE](LICENSE).
