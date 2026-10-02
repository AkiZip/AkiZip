<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Akizip 标志" width="128" height="128" />

# Akizip
一款面向Linux的7zip可视化压缩软件

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![翻译状态](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)
[![博客](https://img.shields.io/badge/blog-akizip.top-orange.svg)](https://blog.akizip.top/)

**语言：** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-HK.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Akizip 截图" width="800" />

</div>

# 关于

### 简介

- 一款面向Linux的7zip可视化压缩软件。
- 使用 GTK 4 和 libadwaita 构建，遵循 GNOME 人机界面指南。
- 以 Flatpak 形式分发，在尽量精简权限的同时通过文件选择器安全访问用户指定的文件。

### 功能

- **格式支持**——可创建 `.7z`、`.zip` 和 `.tar` 归档；可解压 `.rar`、`.gz`、`.bz2`、`.xz`、`.tar.gz`、`.tar.bz2`、`.tar.xz`、`.iso` 等多种格式，并可直接浏览其中大多数格式的内容。
- **智能推荐**——根据源文件内容占比，自动推荐归档参数。
- **压缩设置**——支持手动调整压缩参数和线程数；支持密码保护以及 7z 文件名加密。
- **归档管理**——无需解压即可查看，新建，移动，删除文件、文件列表和归档元数据，支持打开归档内的嵌套归档。
- **解压测试**——可解压整个归档或仅提取选中内容，支持受密码保护的归档，并可在解压前测试归档完整性。
- **后台任务**——复杂任务在后台运行，提供实时进度、剩余时间、超时设置和随时取消功能；日志面板可用于查看命令输出与诊断信息。
- **多种语言**——提供 10 多种语言的界面翻译，并可通过 [Weblate](https://hosted.weblate.org/engage/akizip/) 参与贡献。

### 安装

- Akizip 仅以 Flatpak 形式分发。从清单构建并安装：

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```
<br>


# 开发

### 项目布局

```
akizip/
├── data/                      # AppStream 元信息、.desktop、GSettings schema、D-Bus service、图标
├── docs/                      # 截图和设计说明
├── po/                        # 翻译目录（POTFILES.in、LINGUAS、*.po）
├── readmes/                   # 本 README 的多语言版本
├── scripts/                   # 辅助脚本（如格式检查）
├── src/
│   ├── akizip.in              # 入口启动器（由 meson 配置）
│   ├── akizip.gresource.xml   # 打包 .ui 文件的 GResource 清单
│   ├── AkizipApplication.py   # Adw.Application 单例
│   ├── main.py                # 进程入口
│   ├── job_queue.py           # 单线程后台工作器
│   ├── window.py / window.ui  # 主窗口
│   ├── *.ui                   # 对话框：添加、压缩、解压、首选项、快捷键、移动文件夹选择器
│   ├── plugins/               # 状态和长时间运行的插件（sevenzip、system、status、password、context_menu 等）
│   └── ui/                    # 窗口 mixin（日志面板、信息对话框、添加对话框等）
├── top.akizip.akizip.json     # Flatpak 清单
├── update-po.sh               # 翻译流水线
└── meson.build
```

### 架构简述

Akizip 采用插件化架构，整体由界面、任务队列和功能插件三部分组成：

- **界面**——`src/window.ui` 定义主窗口，`src/ui/` 负责文件列表、对话框和日志面板等交互。
- **应用管理**——`AkizipApplication` 连接界面和各项功能，并记录当前选中的文件、可用命令和后台任务。
- **后台任务**——压缩、解压等耗时操作由 `JobQueue` 在后台依次执行，避免界面卡顿，同时负责进度、取消和超时处理。
- **功能插件**——各个插件将自己的功能注册为应用命令，需要时由界面统一调用。例如，`plugins/sevenzip.py` 调用 7-Zip 完成归档操作，`plugins/system_job.py` 负责文件扫描、智能压缩推荐和文件移动等工作。

简单来说，工作流程是：用户在界面发起操作 → 应用找到对应功能 → 任务在后台执行 → 进度和结果返回界面。

有关扩展插件系统的更深入指南，请参见 [`src/plugins/readme.md`](../src/plugins/readme.md)。

### 翻译

要添加新的语言环境，请将其代码追加到 `po/LINGUAS`，运行 `./update-po.sh`，然后翻译生成的 `.po` 文件。

也可以通过 [Weblate](https://hosted.weblate.org/engage/akizip/) 贡献翻译。

<br>


# 许可证与致谢

### 许可证

Akizip 以 **GNU General Public License v3.0 or later** 发布。完整文本请参见 [`COPYING`](../COPYING)。

随附的 `7zz` 二进制文件由上游 [7-Zip 项目](https://www.7-zip.org/)（www.7-zip.org）提供。软件的部分内容可能使用 GNU LGPL 许可的代码。

### 致谢

- [7-Zip](https://www.7-zip.org/)——开源归档引擎。7-Zip 是 Igor Pavlov 的商标。本项目不隶属于 7-Zip 项目，也未获得其认可。
- [GTK](https://www.gtk.org/) 和 [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita)——工具包和设计库。GTK 是 GNOME Foundation 的商标。
- [PyGObject](https://pygobject.readthedocs.io/)——GTK 及相关组件的 Python 绑定。

### 相关声明

*Akizip 是独立的社区项目，不隶属于 GNOME 项目或 GNOME Foundation，也未获得其认可或赞助。GNOME 和 GNOME 标志是 GNOME Foundation 的商标。*

*本 README 由 AI 翻译。如与英语版本存在任何冲突或不一致，以[英语版本](../README.md)为准。*
