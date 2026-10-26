# Ted Huang's project hub

**English** · [繁體中文](README.zh-TW.md)

The directory of Ted Huang's 23 original public projects, with current scope, status and links, reviewed on 23 October 2026.

**Live:** https://ted-h-com.github.io/ · **Personal mirror:** https://teddashh.github.io/

## What is here

- `hub.json`: the shared project list, grouped descriptions, status and language-specific links. Edit it, then run `python3 kit/render_hub.py .`.
- `site/`: the generated directory, project tiles and redirects, deployed by `.github/workflows/pages.yml`. The workflow renders URLs for the current host.
- `kit/`: the shared bilingual page generator. See [kit/README.md](kit/README.md).
- `docs/`: site architecture and content guidelines. See [docs/README.md](docs/README.md).
- The project list on the [GitHub profile](https://github.com/teddashh) comes from the same `hub.json`, through `python3 kit/render_profile.py <profile-repo>`.

## How project pages work

This repository is the canonical source; the personal hub mirrors it. Most project repositories keep `site/page.json` and use the kit to build their own Pages site under `https://ted-h-com.github.io/<repo>/`. Projects with custom websites keep their own build process; explicit `page` links in `hub.json` preserve their language routes. `freeworkshop-issue-assets` remains under the personal account.

The hub hosts the directory and redirects from older project URLs. Kit pages are static and remember the reader's language choice on the same origin; custom project sites may have different language and asset behavior.

## Validation

Run `python3 kit/test_hub_hosts.py`, `python3 kit/test_render_profile.py` and `node --test kit/flow.test.js`. Render the hub and profile after editing the shared list, and check both languages on mobile and desktop before publishing.

## License

MIT. See [LICENSE](LICENSE).
