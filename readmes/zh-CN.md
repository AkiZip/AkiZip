<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Akizip 标志" width="128" height="128" />

# Akizip

一款面向 GNOME 的现代归档管理器，使用 GTK 4 和 libadwaita 构建。

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)

**语言：** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-TW.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

## 截图

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Akizip 截图" />

</div>

## 关于

**Akizip** 是一款面向 GNOME 桌面的图形化归档工具，使用 GTK 4 和 libadwaita 构建。它以 Flatpak（`top.akizip.akizip`）形式分发，并随附捆绑的 `7zz` 二进制文件，用于处理 7z 和其他归档格式。

Akizip 是图形化应用程序，不是库——它会为所有归档工作调用随附的 `7zz` 可执行文件，支持上游 7-Zip 引擎提供的格式。

## 功能

- **原生 GNOME 体验**——使用 GTK 4 和 libadwaita 构建，遵循 GNOME 人机界面指南。
- **广泛的格式支持**——通过随附的 7-Zip 引擎支持 `.7z`、`.zip`、`.tar`、`.tar.gz`、`.gz`、`.rar`（只读）以及更多格式。
- **压缩和解压**——创建新的归档文件或解包现有归档文件，并显示进度。
- **归档检查**——无需解压即可查看归档元数据和内容。
- **可取消、非阻塞的任务**——长时间运行的操作会在后台工作线程中运行，并可随时取消。
- **日志面板**——提供专用的可停靠窗口，用于查看命令输出和诊断信息。
- **多语言界面**——目前随附英语、简体中文（`zh_CN`）和繁体中文（`zh_HK`）翻译。
- **默认沙盒化**——以 Flatpak 形式分发，并使用最小权限。

## 安装

### Flatpak（推荐）

从清单构建并安装 Flatpak：

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```


## 从源代码构建

你需要 `meson`、`ninja`、GTK 4 开发头文件、libadwaita 开发头文件、PyGObject 和 `gettext`。

```bash
meson setup build
meson compile -C build
meson test    -C build                              # 验证 desktop 文件、AppStream 元信息、GSettings schema
meson install -C build --destdir=/tmp/akizip-stage  # 然后运行 /tmp/akizip-stage/usr/local/bin/akizip
```

启动器（`src/akizip.in`，配置后会变成 `build/src/akizip`）是标准入口点。直接从源代码树运行 `python3 -m akizip.main` 将**无法**工作，因为必须先加载 GResource bundle。

### 在宿主机上运行

`plugins/sevenzip.py` 将随附二进制文件路径硬编码为 `/app/bin/7zz`，该路径只存在于 Flatpak 沙盒内。若要在宿主机上运行，请将 `7zz` 安装到该路径（或创建符号链接），或者临时编辑 `SEVENZIP_PATH` 常量。

## 翻译

翻译工作由一个小型 shell 脚本驱动，而不是由 Meson 驱动：

```bash
./update-po.sh                              # 将字符串提取到 po/akizip.pot，并 msgmerge zh_CN.po 和 zh_HK.po
msgfmt --check po/zh_CN.po -o /dev/null     # 验证目录文件而不编译
```

`po/POTFILES.in` 列出输入文件。`update-po.sh` 按扩展名分派：Python 源码使用 `xgettext --language=Python`，`.ui` 文件使用 Glade，`.desktop.in` / `.metainfo.xml.in` 使用 GNOME ITS 文件。`.gschema.xml` 中的字符串会列出，但会跳过提取（它们由 GLib 在运行时翻译）。

要添加新的语言环境，请将其代码追加到 `po/LINGUAS`，运行 `./update-po.sh`，然后翻译生成的 `.po` 文件。

## 项目布局

```
akizip/
├── data/                      # AppStream 元信息、.desktop、GSettings schema、图标
├── docs/                      # 截图和设计说明
├── po/                        # 翻译目录
├── src/
│   ├── akizip.in              # 入口启动器（由 meson 配置）
│   ├── AkizipApplication.py   # Adw.Application 单例
│   ├── main.py                # 进程入口
│   ├── job_queue.py           # 单线程后台工作器
│   ├── window.py / window.ui  # 主窗口
│   ├── plugins/               # 状态和长时间运行的插件
│   └── ui/                    # 窗口 mixin（日志、信息对话框等）
├── top.akizip.akizip.json     # Flatpak 清单
├── update-po.sh               # 翻译流水线
└── meson.build
```

### 架构简述

- `AkizipApplication` 是一个 `Adw.Application` 单例，拥有三个同级对象：`app.commands`（`"group.action" → callable` 字典）、`app.job_queue`（后台工作器）和 `app.system`（保存当前选择状态的 `sysop()` 实例）。
- **即时插件**（`plugins/system.py`、`plugins/status.py`）是由 UI 同步调用的普通 Python 对象。它们不得阻塞。
- **长时间运行的插件**（`plugins/sevenzip.py`、`plugins/system_job.py`）暴露 `register(commands)` 函数，并通过 `JobQueue` 提交工作。每个 callable 都接受 `timeout=-1` 和 `cancel_event=None`，轮询取消事件，并遵守截止时间。
- 窗口模板位于 `src/window.ui`，并在构建时打包进 GResource。`src/ui/` 中的 mixin 组合成主窗口——`LogPanelMixin` 拥有独立的日志窗口，`InfoDialogMixin` 构建归档信息对话框。

有关扩展插件系统的更深入指南，请参见 [`src/plugins/readme.md`](../src/plugins/readme.md)。

## 许可证

Akizip 以 **GNU General Public License v3.0 or later** 发布。完整文本请参见 [`COPYING`](../COPYING)。

随附的 `7zz` 二进制文件由上游 [7-Zip 项目](https://www.7-zip.org/)（www.7-zip.org）提供。软件的部分内容可能使用 GNU LGPL 许可的代码。

## 致谢

- [7-Zip](https://www.7-zip.org/)——开源归档引擎。7-Zip 是 Igor Pavlov 的商标。本项目不隶属于 7-Zip 项目，也未获得其认可。
- [GTK](https://www.gtk.org/) 和 [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita)——工具包和设计库。GTK 是 GNOME Foundation 的商标。
- [PyGObject](https://pygobject.readthedocs.io/)——GTK 及相关组件的 Python 绑定。

*GNOME 和 GNOME 标志是 GNOME Foundation 的商标。*
