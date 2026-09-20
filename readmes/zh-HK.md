<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Akizip 標誌" width="128" height="128" />

# Akizip
一款面向 Linux 的 7-Zip 圖像化壓縮軟件

[![授權：GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![平台](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![翻譯狀態](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)
[![網誌](https://img.shields.io/badge/blog-akizip.top-orange.svg)](https://blog.akizip.top/)

**語言：** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-HK.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Akizip 截圖" width="800" />

</div>

# 關於

### 簡介

- 一款面向 Linux 的 7-Zip 圖像化壓縮軟件。
- 使用 GTK 4 和 libadwaita 構建，遵循 GNOME 人機介面指南。
- 以 Flatpak 形式發佈，在盡量精簡權限的同時，透過檔案選擇器安全存取用戶指定的檔案。

### 功能

- **格式支援**——可建立 `.7z`、`.zip` 和 `.tar` 壓縮檔；可解壓 `.rar`、`.gz`、`.bz2`、`.xz`、`.tar.gz`、`.tar.bz2`、`.tar.xz`、`.cab`、`.iso`、`.dmg`、`.wim`、`.arj`、`.lzh` 等多種格式，並可直接瀏覽其中大多數格式的內容。
- **智能建議**——根據來源檔案的內容比例，自動建議壓縮參數。
- **壓縮設定**——支援手動調整壓縮參數和執行緒數；支援密碼保護以及 7z 檔案名稱加密。
- **壓縮檔管理**——毋須解壓即可查看、新增、移動和刪除壓縮檔內的檔案，亦可查看檔案清單和壓縮檔中繼資料，並開啟嵌套壓縮檔。
- **解壓測試**——可解壓整個壓縮檔或只提取所選項目，支援受密碼保護的壓縮檔，並可在解壓前測試完整性。
- **背景工作**——複雜操作會在背景執行，提供即時進度、預計剩餘時間、逾時設定和隨時取消功能；日誌面板可用於查看指令輸出和診斷資訊。
- **多種語言**——提供超過 10 種語言的介面翻譯，並可透過 [Weblate](https://hosted.weblate.org/engage/akizip/) 參與貢獻。

### 安裝

- Akizip 僅以 Flatpak 形式發佈。請從清單構建並安裝：

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```
<br>


# 開發

### 專案佈局

```
akizip/
├── data/                      # AppStream 中繼資料、.desktop、GSettings schema、D-Bus service、圖示
├── docs/                      # 截圖和設計說明
├── po/                        # 翻譯目錄（POTFILES.in、LINGUAS、*.po）
├── readmes/                   # 本 README 的多語言版本
├── scripts/                   # 輔助指令碼（例如格式檢查）
├── src/
│   ├── akizip.in              # 入口啟動器（由 Meson 設定）
│   ├── akizip.gresource.xml   # 打包 .ui 檔案的 GResource 清單
│   ├── AkizipApplication.py   # Adw.Application 單例
│   ├── main.py                # 程序入口
│   ├── job_queue.py           # 單執行緒背景工作器
│   ├── window.py / window.ui  # 主視窗
│   ├── *.ui                   # 新增、壓縮、解壓、偏好設定、快捷鍵和資料夾選擇器對話框
│   ├── plugins/               # 狀態及長時間執行的插件（sevenzip、system、status、password、context_menu 等）
│   └── ui/                    # 視窗 mixin（日誌面板、資訊對話框、新增對話框等）
├── top.akizip.akizip.json     # Flatpak 清單
├── update-po.sh               # 翻譯流程
└── meson.build
```

### 架構簡述

Akizip 採用插件化架構，整體由介面、工作佇列和功能插件三部分組成：

- **介面**——`src/window.ui` 定義主視窗，`src/ui/` 負責檔案清單、對話框和日誌面板等互動。
- **應用程式管理**——`AkizipApplication` 連接介面和各項功能，並記錄目前選取的檔案、可用指令和背景工作。
- **背景工作**——壓縮、解壓等耗時操作由 `JobQueue` 在背景依次執行，避免介面停頓，同時負責進度、取消和逾時處理。
- **功能插件**——各插件把自己的功能註冊為應用程式指令，需要時由介面統一呼叫。例如，`plugins/sevenzip.py` 呼叫 7-Zip 完成壓縮檔操作，`plugins/system_job.py` 則負責檔案掃描、智能壓縮建議和檔案移動等工作。

簡單來說，工作流程是：用戶在介面發起操作 → 應用程式找到對應功能 → 工作在背景執行 → 進度和結果返回介面。

有關擴充插件系統的深入指南，請參閱 [`src/plugins/readme.md`](../src/plugins/readme.md)。

### 翻譯

如要新增語言環境，請把其代碼加入 `po/LINGUAS`，執行 `./update-po.sh`，然後翻譯產生的 `.po` 檔案。

也可以透過 [Weblate](https://hosted.weblate.org/engage/akizip/) 貢獻翻譯。

<br>


# 授權與致謝

### 授權

Akizip 以 **GNU General Public License v3.0 or later** 發佈。完整條款請參閱 [`COPYING`](../COPYING)。

隨附的 `7zz` 執行檔由上游 [7-Zip 專案](https://www.7-zip.org/)（www.7-zip.org）提供。本軟件的部分內容可能使用以 GNU LGPL 授權的程式碼。

### 致謝

- [7-Zip](https://www.7-zip.org/)——開源壓縮引擎。7-Zip 是 Igor Pavlov 的商標。本專案與 7-Zip 專案並無關聯，亦未獲其認可。
- [GTK](https://www.gtk.org/) 和 [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita)——工具包和設計程式庫。GTK 是 GNOME Foundation 的商標。
- [PyGObject](https://pygobject.readthedocs.io/)——GTK 及相關組件的 Python 綁定。

### 相關聲明

*Akizip 是獨立的社群專案，與 GNOME Project 或 GNOME Foundation 並無關聯，亦未獲其認可、贊助或支持。GNOME 和 GNOME 標誌是 GNOME Foundation 的商標。*

*本 README 由 AI 翻譯。如與英文版本存在任何衝突或不一致，以[英文版本](../README.md)為準。*
