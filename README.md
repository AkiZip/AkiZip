<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Akizip Logo" width="128" height="128" />

# Akizip
A visual 7-Zip archive manager for Linux

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![Translation status](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)
[![Blog](https://img.shields.io/badge/blog-akizip.top-orange.svg)](https://blog.akizip.top/)

**Languages:** [English](README.md) | [简体中文](readmes/zh-CN.md) | [繁體中文](readmes/zh-HK.md) | [日本語](readmes/ja.md) | [한국어](readmes/ko.md) | [Español](readmes/es.md) | [Italiano](readmes/it.md)

</div>

---

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Akizip Screenshot" width="800" />

</div>

# About

### Overview

- A visual 7-Zip archive manager for Linux.
- Built with GTK 4 and libadwaita in accordance with the GNOME Human Interface Guidelines.
- Distributed as a Flatpak, with access to user-selected files through the file chooser while keeping permissions as limited as practical.

### Features

- **Format support** — Create `.7z`, `.zip`, and `.tar` archives; extract `.rar`, `.gz`, `.bz2`, `.xz`, `.tar.gz`, `.tar.bz2`, `.tar.xz`, `.cab`, `.iso`, `.dmg`, `.wim`, `.arj`, `.lzh`, and many other formats; and browse the contents of most supported formats.
- **Smart recommendations** — Automatically recommend archive parameters based on the composition of the source files.
- **Compression settings** — Manually adjust compression parameters and thread count; use password protection and 7z file-name encryption.
- **Archive management** — View, create, move, and delete files inside archives without extracting them; inspect file lists and archive metadata; and open nested archives.
- **Extraction testing** — Extract an entire archive or only selected items, work with password-protected archives, and test archive integrity before extraction.
- **Background jobs** — Run complex operations in the background with real-time progress, estimated time remaining, configurable timeouts, and cancellation; use the logs panel to inspect command output and diagnostics.
- **Multiple languages** — Use the interface in more than 10 languages and contribute translations through [Weblate](https://hosted.weblate.org/engage/akizip/).

### Installation

- Akizip is distributed exclusively as a Flatpak. Build and install it from the manifest:

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```
<br>


# Development

### Project layout

```
akizip/
├── data/                      # AppStream metadata, .desktop file, GSettings schema, D-Bus service, and icons
├── docs/                      # Screenshots and design notes
├── po/                        # Translation catalogs (POTFILES.in, LINGUAS, *.po)
├── readmes/                   # Translated versions of this README
├── scripts/                   # Helper scripts, such as format checks
├── src/
│   ├── akizip.in              # Entry-point launcher configured by Meson
│   ├── akizip.gresource.xml   # GResource manifest that bundles .ui files
│   ├── AkizipApplication.py   # Adw.Application singleton
│   ├── main.py                # Process entry point
│   ├── job_queue.py           # Single-threaded background worker
│   ├── window.py / window.ui  # Main window
│   ├── *.ui                   # Dialogs for add, compress, extract, preferences, shortcuts, and folder selection
│   ├── plugins/               # Status and long-running plugins (sevenzip, system, status, password, context_menu, etc.)
│   └── ui/                    # Window mixins for the logs panel, information dialog, add dialog, and more
├── top.akizip.akizip.json     # Flatpak manifest
├── update-po.sh               # Translation workflow
└── meson.build
```

### Architecture overview

Akizip uses a plugin-based architecture made up of three main parts: the interface, a job queue, and feature plugins.

- **Interface** — `src/window.ui` defines the main window, while `src/ui/` handles interactions such as the file list, dialogs, and logs panel.
- **Application management** — `AkizipApplication` connects the interface to the available features and tracks the selected file, registered commands, and background jobs.
- **Background jobs** — `JobQueue` runs time-consuming operations such as compression and extraction one at a time in the background, keeping the interface responsive while handling progress, cancellation, and timeouts.
- **Feature plugins** — Each plugin registers its features as application commands that the interface can call when needed. For example, `plugins/sevenzip.py` uses 7-Zip for archive operations, while `plugins/system_job.py` handles file scanning, smart compression recommendations, and file moves.

In short: the user starts an operation in the interface → the application finds the corresponding feature → the job runs in the background → progress and results return to the interface.

For a deeper guide to extending the plugin system, see [`src/plugins/readme.md`](src/plugins/readme.md).

### Translations

To add a new locale, append its code to `po/LINGUAS`, run `./update-po.sh`, and translate the generated `.po` file.

Translations can also be contributed through [Weblate](https://hosted.weblate.org/engage/akizip/).

<br>


# License and acknowledgements

### License

Akizip is released under the **GNU General Public License v3.0 or later**. See [`COPYING`](COPYING) for the full text.

The bundled `7zz` binary is provided by the upstream [7-Zip project](https://www.7-zip.org/) (www.7-zip.org). Portions of the software may use code licensed under the GNU LGPL.

### Acknowledgements

- [7-Zip](https://www.7-zip.org/) — the open-source archive engine. 7-Zip is a trademark of Igor Pavlov. This project is not affiliated with or endorsed by the 7-Zip project.
- [GTK](https://www.gtk.org/) and [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) — the toolkit and design library. GTK is a trademark of the GNOME Foundation.
- [PyGObject](https://pygobject.readthedocs.io/) — Python bindings for GTK and related components.

### Notices

*Akizip is an independent community project and is not affiliated with, endorsed by, or sponsored by the GNOME Project or the GNOME Foundation. GNOME and the GNOME logo are trademarks of the GNOME Foundation.*

*Translations of this README may be assisted by AI. If a translated version conflicts with or differs from this English version, this English version takes precedence.*
