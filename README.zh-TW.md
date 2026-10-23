# Ted Huang 專案總目錄

[English](README.md) · **繁體中文**

收錄 Ted Huang 的 23 個原創公開專案，整理目前範圍、進度和入口；最近核對日期為 2026 年 10 月 23 日。

**網站：** https://ted-h-com.github.io/?lang=zh-TW · **個人鏡像：** https://teddashh.github.io/?lang=zh-TW

## 這裡有什麼

- `hub.json`：共用專案清單、分組介紹、狀態和各語言入口。修改後執行 `python3 kit/render_hub.py .`。
- `site/`：產生的目錄、專案圖卡和舊網址轉址，由 `.github/workflows/pages.yml` 依目前網域產生網址後部署。
- `kit/`：共用的雙語頁面產生器，說明見 [kit/README.md](kit/README.md)。
- [GitHub 個人頁](https://github.com/teddashh)的專案清單也來自同一份 `hub.json`，用 `python3 kit/render_profile.py <profile-repo>` 產生。

## 專案介紹頁怎麼運作

這個 repo 是主要來源，個人帳號的目錄會同步內容。多數專案以自己的 `site/page.json` 和工具組產生介紹頁，發布於 `https://ted-h-com.github.io/<repo>/`。有自訂網站的專案沿用自己的建置流程；`hub.json` 的 `page` 欄位保留各站正確的語言路徑。`freeworkshop-issue-assets` 仍在個人帳號下。

總目錄也保留舊專案網址的轉址。工具組產生的頁面是靜態檔，同網域會記住讀者的語言選擇；各專案的自訂網站可以有不同的語言和素材處理方式。

## 驗證

執行 `python3 kit/test_hub_hosts.py`、`python3 kit/test_render_profile.py` 和 `node --test kit/flow.test.js`。修改共用清單後重新產生目錄和個人頁，發布前檢查中英文的手機與桌面版面。

## 授權

MIT，見 [LICENSE](LICENSE)。
