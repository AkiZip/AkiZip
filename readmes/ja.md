<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Akizip ロゴ" width="128" height="128" />

# Akizip

GTK 4 と libadwaita で構築された、GNOME 向けのモダンなアーカイブマネージャーです。

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![翻訳状況](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)
[![ブログ](https://img.shields.io/badge/blog-akizip.top-orange.svg)](https://blog.akizip.top/)

**言語:** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-HK.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

## スクリーンショット

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Akizip スクリーンショット" />

</div>

## 概要

**Akizip** は、GTK 4 と libadwaita で構築された GNOME デスクトップ向けのグラフィカルなアーカイブユーティリティです。Flatpak（`top.akizip.akizip`）として配布され、7z やその他のアーカイブ形式を扱うための `7zz` バイナリを同梱しています。

Akizip はライブラリではなくグラフィカルアプリケーションです。すべてのアーカイブ処理で同梱の `7zz` 実行ファイルを呼び出し、上流の 7-Zip エンジンが提供する形式をサポートします。

## 機能

- **ネイティブな GNOME 体験** — GTK 4 と libadwaita で構築され、GNOME ヒューマンインターフェースガイドラインに従っています。
- **幅広い形式のサポート** — 同梱の 7-Zip エンジンにより、`.7z`、`.zip`、`.tar`、`.tar.gz`、`.gz`、`.rar`（読み取り専用）など、多くの形式をサポートします。
- **圧縮と展開** — 進捗表示付きで新しいアーカイブを作成したり、既存のアーカイブを展開したりできます。
- **アーカイブの確認** — 展開せずにアーカイブのメタデータと内容を表示できます。
- **キャンセル可能で非ブロッキングなジョブ** — 長時間実行される操作はバックグラウンドワーカースレッドで実行され、いつでもキャンセルできます。
- **ログパネル** — コマンド出力と診断情報を確認するための専用のドッキング可能なウィンドウを備えています。
- **多言語 UI** — 英語、中国語、スペイン語、フランス語、イタリア語、ロシア語など、10 以上の言語の翻訳を同梱しています。[Weblate](https://hosted.weblate.org/engage/akizip/) を通じて貢献されています。
- **デフォルトでサンドボックス化** — 最小限の権限を持つ Flatpak として配布されます。

## インストール

Akizip は Flatpak 専用に配布されています。マニフェストからビルドしてインストールしてください。

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```

## 翻訳

翻訳作業は Meson ではなく、小さな shell スクリプトで行います。

```bash
./update-po.sh                              # 文字列を po/akizip.pot に抽出し、po/LINGUAS の全カタログを msgmerge する
msgfmt --check po/zh_CN.po -o /dev/null     # コンパイルせずにカタログを検証する
```

`po/POTFILES.in` には入力ファイルが列挙されています。`update-po.sh` は拡張子ごとに処理を分けます。Python ソースは `xgettext --language=Python`、`.ui` ファイルは Glade、`.desktop.in` / `.metainfo.xml.in` は GNOME ITS ファイルを使用します。`.gschema.xml` 内の文字列は一覧には含まれますが、抽出はスキップされます（GLib により実行時に翻訳されます）。

新しいロケールを追加するには、そのコードを `po/LINGUAS` に追記し、`./update-po.sh` を実行して、生成された `.po` ファイルを翻訳します。

翻訳は [Weblate](https://hosted.weblate.org/engage/akizip/) からも貢献できます。

## プロジェクト構成

```
akizip/
├── data/                      # AppStream メタ情報、.desktop、GSettings schema、D-Bus サービス、アイコン
├── docs/                      # スクリーンショットと設計メモ
├── po/                        # 翻訳カタログ（POTFILES.in、LINGUAS、*.po）
├── readmes/                   # この README の各国語版
├── scripts/                   # ヘルパースクリプト（フォーマットチェックなど）
├── src/
│   ├── akizip.in              # エントリーポイントランチャー（meson により設定）
│   ├── akizip.gresource.xml   # .ui ファイルをバンドルする GResource マニフェスト
│   ├── AkizipApplication.py   # Adw.Application シングルトン
│   ├── main.py                # プロセスエントリー
│   ├── job_queue.py           # 単一スレッドのバックグラウンドワーカー
│   ├── window.py / window.ui  # メインウィンドウ
│   ├── *.ui                   # ダイアログ：追加、圧縮、展開、設定、ショートカット、移動先フォルダー選択
│   ├── plugins/               # 状態と長時間実行プラグイン（sevenzip、system、status、password、context_menu など）
│   └── ui/                    # ウィンドウ mixin（ログパネル、情報ダイアログ、追加ダイアログなど）
├── top.akizip.akizip.json     # Flatpak マニフェスト
├── update-po.sh               # 翻訳パイプライン
└── meson.build
```

### アーキテクチャ概要

- `AkizipApplication` は `Adw.Application` シングルトンで、3 つの関連オブジェクトを所有します。`app.commands`（`"group.action" → callable` の辞書）、`app.job_queue`（バックグラウンドワーカー）、`app.system`（現在の選択状態を保持する `sysop()` インスタンス）です。
- **即時プラグイン**（`plugins/system.py`、`plugins/status.py`）は、UI から同期的に呼び出される通常の Python オブジェクトです。ブロックしてはいけません。
- **長時間実行プラグイン**（`plugins/sevenzip.py`、`plugins/system_job.py`）は `register(commands)` 関数を公開し、`JobQueue` を通じて作業を投入します。各 callable は `timeout=-1` と `cancel_event=None` を受け取り、キャンセルイベントをポーリングし、期限を尊重します。
- ウィンドウテンプレートは `src/window.ui` にあり、ビルド時に GResource へバンドルされます。`src/ui/` の mixin がメインウィンドウを構成します。`LogPanelMixin` は別個のログウィンドウを所有し、`InfoDialogMixin` はアーカイブ情報ダイアログを構築します。

プラグインシステムを拡張するための詳しいガイドは、[`src/plugins/readme.md`](../src/plugins/readme.md) を参照してください。

## ライセンス

Akizip は **GNU General Public License v3.0 or later** の下で公開されています。全文は [`COPYING`](../COPYING) を参照してください。

同梱の `7zz` バイナリは、上流の [7-Zip プロジェクト](https://www.7-zip.org/)（www.7-zip.org）によって提供されています。ソフトウェアの一部には GNU LGPL でライセンスされたコードが使われている場合があります。

## 謝辞

- [7-Zip](https://www.7-zip.org/) — オープンソースのアーカイブエンジンです。7-Zip は Igor Pavlov の商標です。このプロジェクトは 7-Zip プロジェクトと提携しておらず、承認も受けていません。
- [GTK](https://www.gtk.org/) と [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) — ツールキットとデザインライブラリです。GTK は GNOME Foundation の商標です。
- [PyGObject](https://pygobject.readthedocs.io/) — GTK と関連コンポーネントの Python バインディングです。

*Akizip は独立したコミュニティプロジェクトであり、GNOME プロジェクトまたは GNOME Foundation と提携、承認、またはスポンサー関係にはありません。GNOME および GNOME ロゴは GNOME Foundation の商標です。*

---

*この README は AI によって翻訳されました。英語版と矛盾または相違がある場合は、[英語版](../README.md)が優先されます。*
