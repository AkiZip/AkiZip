<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Akizip ロゴ" width="128" height="128" />

# Akizip
Linux 向けの 7-Zip GUI アーカイブマネージャー

[![ライセンス: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![プラットフォーム](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![翻訳状況](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)
[![ブログ](https://img.shields.io/badge/blog-akizip.top-orange.svg)](https://blog.akizip.top/)

**言語:** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-HK.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Akizip スクリーンショット" width="800" />

</div>

# 概要

### 紹介

- Linux 向けの 7-Zip GUI アーカイブマネージャーです。
- GTK 4 と libadwaita で構築され、GNOME Human Interface Guidelines に準拠しています。
- Flatpak として配布され、権限を可能な限り抑えながら、ファイル選択画面を通じてユーザーが指定したファイルへ安全にアクセスします。

### 機能

- **対応形式** — `.7z`、`.zip`、`.tar` アーカイブを作成できます。`.rar`、`.gz`、`.bz2`、`.xz`、`.tar.gz`、`.tar.bz2`、`.tar.xz`、`.cab`、`.iso`、`.dmg`、`.wim`、`.arj`、`.lzh` などの多くの形式を展開でき、その大半は内容を直接閲覧できます。
- **スマート推奨** — 元ファイルの構成に基づいて、アーカイブのパラメーターを自動的に推奨します。
- **圧縮設定** — 圧縮パラメーターとスレッド数を手動で調整でき、パスワード保護と 7z のファイル名暗号化にも対応します。
- **アーカイブ管理** — 展開せずにアーカイブ内のファイルを表示、作成、移動、削除できます。ファイル一覧とアーカイブのメタデータを確認し、入れ子になったアーカイブを開くこともできます。
- **展開と整合性テスト** — アーカイブ全体または選択した項目だけを展開でき、パスワード保護されたアーカイブに対応し、展開前に整合性をテストできます。
- **バックグラウンドジョブ** — 複雑な処理をバックグラウンドで実行し、リアルタイムの進捗、推定残り時間、タイムアウト設定、キャンセル機能を提供します。ログパネルではコマンド出力と診断情報を確認できます。
- **多言語対応** — 10 を超える言語のインターフェースを利用でき、[Weblate](https://hosted.weblate.org/engage/akizip/) から翻訳に参加できます。

### インストール

- Akizip は Flatpak のみで配布されています。マニフェストからビルドしてインストールしてください。

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```
<br>


# 開発

### プロジェクト構成

```
akizip/
├── data/                      # AppStream メタデータ、.desktop、GSettings schema、D-Bus service、アイコン
├── docs/                      # スクリーンショットと設計メモ
├── po/                        # 翻訳カタログ（POTFILES.in、LINGUAS、*.po）
├── readmes/                   # この README の各言語版
├── scripts/                   # 形式チェックなどの補助スクリプト
├── src/
│   ├── akizip.in              # Meson で設定されるエントリーポイント
│   ├── akizip.gresource.xml   # .ui ファイルをまとめる GResource マニフェスト
│   ├── AkizipApplication.py   # Adw.Application シングルトン
│   ├── main.py                # プロセスのエントリーポイント
│   ├── job_queue.py           # 単一スレッドのバックグラウンドワーカー
│   ├── window.py / window.ui  # メインウィンドウ
│   ├── *.ui                   # 追加、圧縮、展開、設定、ショートカット、フォルダー選択の各ダイアログ
│   ├── plugins/               # 状態および長時間処理用プラグイン（sevenzip、system、status、password、context_menu など）
│   └── ui/                    # ログパネル、情報、追加ダイアログなどのウィンドウ mixin
├── top.akizip.akizip.json     # Flatpak マニフェスト
├── update-po.sh               # 翻訳ワークフロー
└── meson.build
```

### アーキテクチャ概要

Akizip は、インターフェース、ジョブキュー、機能プラグインの 3 つを中心とするプラグイン型アーキテクチャを採用しています。

- **インターフェース** — `src/window.ui` がメインウィンドウを定義し、`src/ui/` がファイル一覧、ダイアログ、ログパネルなどの操作を担当します。
- **アプリケーション管理** — `AkizipApplication` がインターフェースと各機能を結び付け、選択中のファイル、利用可能なコマンド、バックグラウンドジョブを管理します。
- **バックグラウンドジョブ** — `JobQueue` が圧縮や展開などの時間のかかる処理をバックグラウンドで順番に実行し、画面を停止させずに進捗、キャンセル、タイムアウトを処理します。
- **機能プラグイン** — 各プラグインは機能をアプリケーションコマンドとして登録し、必要なときにインターフェースから呼び出されます。たとえば、`plugins/sevenzip.py` は 7-Zip を使ったアーカイブ操作を、`plugins/system_job.py` はファイルのスキャン、スマート圧縮推奨、ファイル移動を担当します。

処理の流れは、ユーザーが画面から操作を開始 → アプリケーションが対応する機能を検索 → ジョブをバックグラウンドで実行 → 進捗と結果を画面へ返す、となります。

プラグインシステムの拡張方法については、[`src/plugins/readme.md`](../src/plugins/readme.md) を参照してください。

### 翻訳

新しいロケールを追加するには、そのコードを `po/LINGUAS` に追加し、`./update-po.sh` を実行して、生成された `.po` ファイルを翻訳してください。

[Weblate](https://hosted.weblate.org/engage/akizip/) から翻訳に参加することもできます。

<br>


# ライセンスと謝辞

### ライセンス

Akizip は **GNU General Public License v3.0 or later** の下で公開されています。全文は [`COPYING`](../COPYING) を参照してください。

同梱の `7zz` バイナリは、上流の [7-Zip プロジェクト](https://www.7-zip.org/)（www.7-zip.org）によって提供されています。本ソフトウェアの一部には GNU LGPL でライセンスされたコードが含まれる場合があります。

### 謝辞

- [7-Zip](https://www.7-zip.org/) — オープンソースのアーカイブエンジンです。7-Zip は Igor Pavlov の商標です。本プロジェクトは 7-Zip プロジェクトとは無関係であり、その承認も受けていません。
- [GTK](https://www.gtk.org/) と [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) — ツールキットとデザインライブラリです。GTK は GNOME Foundation の商標です。
- [PyGObject](https://pygobject.readthedocs.io/) — GTK および関連コンポーネントの Python バインディングです。

### 関連事項

*Akizip は独立したコミュニティプロジェクトであり、GNOME Project または GNOME Foundation との提携、承認、支援関係はありません。GNOME および GNOME ロゴは GNOME Foundation の商標です。*

*この README は AI によって翻訳されました。英語版と矛盾または相違がある場合は、[英語版](../README.md)が優先されます。*
