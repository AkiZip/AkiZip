<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Akizip 標誌" width="128" height="128" />

# Akizip

一款面向 GNOME 的現代封存檔管理器，使用 GTK 4 和 libadwaita 建置。

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)

**語言：** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-TW.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

## 截圖

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Akizip 截圖" />

</div>

## 關於

**Akizip** 是一款面向 GNOME 桌面的圖形化封存檔工具，使用 GTK 4 和 libadwaita 建置。它以 Flatpak（`top.akizip.akizip`）形式發佈，並隨附捆綁的 `7zz` 二進位檔，用於處理 7z 和其他封存檔格式。

Akizip 是圖形化應用程式，不是函式庫——它會為所有封存檔工作呼叫隨附的 `7zz` 可執行檔，支援上游 7-Zip 引擎提供的格式。

## 功能

- **原生 GNOME 體驗**——使用 GTK 4 和 libadwaita 建置，遵循 GNOME 人機介面指南。
- **廣泛的格式支援**——透過隨附的 7-Zip 引擎支援 `.7z`、`.zip`、`.tar`、`.tar.gz`、`.gz`、`.rar`（唯讀）以及更多格式。
- **壓縮和解壓縮**——建立新的封存檔或解包現有封存檔，並顯示進度。
- **封存檔檢查**——無需解壓縮即可查看封存檔中繼資料和內容。
- **可取消、非阻塞的工作**——長時間執行的操作會在背景工作執行緒中執行，並可隨時取消。
- **日誌面板**——提供專用的可停駐視窗，用於查看命令輸出和診斷資訊。
- **多語言介面**——目前隨附英文、簡體中文（`zh_CN`）和繁體中文（`zh_HK`）翻譯。
- **預設沙盒化**——以 Flatpak 形式發佈，並使用最小權限。

## 安裝

### Flatpak（建議）

從清單建置並安裝 Flatpak：

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```


## 從原始碼建置

你需要 `meson`、`ninja`、GTK 4 開發標頭檔、libadwaita 開發標頭檔、PyGObject 和 `gettext`。

```bash
meson setup build
meson compile -C build
meson test    -C build                              # 驗證 desktop 檔案、AppStream 中繼資訊、GSettings schema
meson install -C build --destdir=/tmp/akizip-stage  # 然後執行 /tmp/akizip-stage/usr/local/bin/akizip
```

啟動器（`src/akizip.in`，設定後會變成 `build/src/akizip`）是標準入口點。直接從原始碼樹執行 `python3 -m akizip.main` 將**無法**運作，因為必須先載入 GResource bundle。

### 在主機上執行

`plugins/sevenzip.py` 將隨附二進位檔路徑硬編碼為 `/app/bin/7zz`，該路徑只存在於 Flatpak 沙盒內。若要在主機上執行，請將 `7zz` 安裝到該路徑（或建立符號連結），或者暫時編輯 `SEVENZIP_PATH` 常數。

## 翻譯

翻譯工作由一個小型 shell 腳本驅動，而不是由 Meson 驅動：

```bash
./update-po.sh                              # 將字串提取到 po/akizip.pot，並 msgmerge zh_CN.po 和 zh_HK.po
msgfmt --check po/zh_CN.po -o /dev/null     # 驗證目錄檔而不編譯
```

`po/POTFILES.in` 列出輸入檔案。`update-po.sh` 按副檔名分派：Python 原始碼使用 `xgettext --language=Python`，`.ui` 檔案使用 Glade，`.desktop.in` / `.metainfo.xml.in` 使用 GNOME ITS 檔案。`.gschema.xml` 中的字串會列出，但會跳過提取（它們由 GLib 在執行階段翻譯）。

要新增新的語言環境，請將其代碼追加到 `po/LINGUAS`，執行 `./update-po.sh`，然後翻譯產生的 `.po` 檔案。

## 專案佈局

```
akizip/
├── data/                      # AppStream 中繼資訊、.desktop、GSettings schema、圖示
├── docs/                      # 截圖和設計說明
├── po/                        # 翻譯目錄
├── src/
│   ├── akizip.in              # 入口啟動器（由 meson 設定）
│   ├── AkizipApplication.py   # Adw.Application 單例
│   ├── main.py                # 程序入口
│   ├── job_queue.py           # 單執行緒背景工作器
│   ├── window.py / window.ui  # 主視窗
│   ├── plugins/               # 狀態和長時間執行的外掛
│   └── ui/                    # 視窗 mixin（日誌、資訊對話框等）
├── top.akizip.akizip.json     # Flatpak 清單
├── update-po.sh               # 翻譯流程
└── meson.build
```

### 架構簡述

- `AkizipApplication` 是一個 `Adw.Application` 單例，擁有三個同級物件：`app.commands`（`"group.action" → callable` 字典）、`app.job_queue`（背景工作器）和 `app.system`（保存目前選取狀態的 `sysop()` 實例）。
- **即時外掛**（`plugins/system.py`、`plugins/status.py`）是由 UI 同步呼叫的普通 Python 物件。它們不得阻塞。
- **長時間執行的外掛**（`plugins/sevenzip.py`、`plugins/system_job.py`）暴露 `register(commands)` 函數，並透過 `JobQueue` 提交工作。每個 callable 都接受 `timeout=-1` 和 `cancel_event=None`，輪詢取消事件，並遵守截止時間。
- 視窗模板位於 `src/window.ui`，並在建置時打包進 GResource。`src/ui/` 中的 mixin 組合成主視窗——`LogPanelMixin` 擁有獨立的日誌視窗，`InfoDialogMixin` 建置封存檔資訊對話框。

有關擴充外掛系統的更深入指南，請參見 [`src/plugins/readme.md`](../src/plugins/readme.md)。

## 授權

Akizip 以 **GNU General Public License v3.0 or later** 發佈。完整文字請參見 [`COPYING`](../COPYING)。

隨附的 `7zz` 二進位檔由上游 [7-Zip 專案](https://www.7-zip.org/)（www.7-zip.org）提供。軟體的部分內容可能使用 GNU LGPL 授權的程式碼。

## 致謝

- [7-Zip](https://www.7-zip.org/)——開源封存檔引擎。7-Zip 是 Igor Pavlov 的商標。本專案不隸屬於 7-Zip 專案，也未獲得其認可。
- [GTK](https://www.gtk.org/) 和 [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita)——工具包和設計函式庫。GTK 是 GNOME Foundation 的商標。
- [PyGObject](https://pygobject.readthedocs.io/)——GTK 及相關元件的 Python 綁定。

*GNOME 和 GNOME 標誌是 GNOME Foundation 的商標。*
