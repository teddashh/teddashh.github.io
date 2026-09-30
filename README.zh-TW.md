# teddashh.github.io

[English](README.md) · **繁體中文**

Ted Huang 開源專案的總目錄，以及產生每個專案介紹頁的工具組。

**網站：** https://teddashh.github.io/?lang=zh-TW

## 這裡有什麼

- `hub.json`：專案清單（分組、一句話介紹、目前狀態）。修改後執行 `python3 kit/render_hub.py .`
- `site/`：產生出來的目錄頁，由 `.github/workflows/pages.yml` 部署。
- `kit/`：每個專案 repo 共用的頁面產生器，說明見 [kit/README.md](kit/README.md)。
- [GitHub 個人頁](https://github.com/teddashh)上的專案清單也來自同一份 `hub.json`，用 `python3 kit/render_profile.py <profile-repo>` 產生。

## 專案介紹頁怎麼運作

每個專案 repo 各自保存 `site/page.json`。工具組把它轉成中英雙語頁面，放在該 repo 的 `site/`，再由該 repo 自己的 Pages workflow 發布到 `https://teddashh.github.io/<repo>/`。這個 repo 只放根目錄的總目錄頁和工具組。

所有頁面都是靜態檔，不向第三方發出任何請求；因為同一個網域，讀者選的語言會在各專案之間沿用。

## 授權

MIT，見 [LICENSE](LICENSE)。
