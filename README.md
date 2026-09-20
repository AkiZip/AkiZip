<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Akizip Logo" width="128" height="128" />

# Akizip

A modern archive manager for GNOME, built with GTK 4 and libadwaita.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![Translation status](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)
[![Blog](https://img.shields.io/badge/blog-akizip.top-orange.svg)](https://blog.akizip.top/)

**Languages:** [English](README.md) | [简体中文](readmes/zh-CN.md) | [繁體中文](readmes/zh-HK.md) | [日本語](readmes/ja.md) | [한국어](readmes/ko.md) | [Español](readmes/es.md) | [Italiano](readmes/it.md)

</div>

---

## Screenshot

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Akizip Screenshot" />

</div>

## About

**Akizip** is a graphical archive utility for the GNOME desktop, built with GTK 4 and libadwaita. It is distributed as a Flatpak (`top.akizip.akizip`) and ships with a bundled `7zz` binary for handling 7z and other archive formats.

Akizip is a graphical application, not a library — it shells out to the bundled `7zz` executable for all archive work, supporting the formats provided by the upstream 7-Zip engine.

## Features

- **Native GNOME experience** — built with GTK 4 and libadwaita, following the GNOME Human Interface Guidelines.
- **Wide format support** — `.7z`, `.zip`, `.tar`, `.tar.gz`, `.gz`, `.rar` (read-only), and many more via the bundled 7-Zip engine.
- **Compression and extraction** — create new archives or unpack existing ones with progress reporting.
- **Archive inspection** — view archive metadata and contents without extracting.
- **Cancellable, non-blocking jobs** — long-running operations run on a background worker thread and can be cancelled at any time.
- **Logs panel** — a dedicated, dockable window for inspecting command output and diagnostics.
- **Multilingual UI** — ships with translations for 10+ languages (including English, Chinese, Spanish, French, Italian, Russian, and more), contributed via [Weblate](https://hosted.weblate.org/engage/akizip/).
- **Sandboxed by default** — distributed as a Flatpak with minimal permissions.

## Installation

Akizip is distributed exclusively as a Flatpak. Build and install it from the manifest:

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```

## Translations

Translation work is driven by a small shell script, not by Meson:

```bash
./update-po.sh                              # extract strings into po/akizip.pot and msgmerge all catalogs in po/LINGUAS
msgfmt --check po/zh_CN.po -o /dev/null     # validate a catalog without compiling
```

`po/POTFILES.in` lists the inputs. `update-po.sh` dispatches by extension: Python sources via `xgettext --language=Python`, `.ui` files via Glade, and `.desktop.in` / `.metainfo.xml.in` via the GNOME ITS file. Strings in `.gschema.xml` are listed but skipped from extraction (they are translated at runtime by GLib).

To add a new locale, append its code to `po/LINGUAS`, run `./update-po.sh`, and translate the generated `.po` file.

Translations can also be contributed through [Weblate](https://hosted.weblate.org/engage/akizip/).

## Project layout

```
akizip/
├── data/                      # AppStream metainfo, .desktop, GSettings schema, D-Bus service, icons
├── docs/                      # screenshots and design notes
├── po/                        # translation catalogs (POTFILES.in, LINGUAS, *.po)
├── readmes/                   # localized versions of this README
├── scripts/                   # helper scripts (e.g. format checking)
├── src/
│   ├── akizip.in              # entry-point launcher (configured by meson)
│   ├── akizip.gresource.xml   # GResource manifest bundling the .ui files
│   ├── AkizipApplication.py   # Adw.Application singleton
│   ├── main.py                # process entry
│   ├── job_queue.py           # single-thread background worker
│   ├── window.py / window.ui  # main window
│   ├── *.ui                   # dialogs: add, compress, extract, preferences, shortcuts, move-folder chooser
│   ├── plugins/               # state and long-running plugins (sevenzip, system, status, password, context_menu, ...)
│   └── ui/                    # window mixins (logs panel, info dialog, add dialog, ...)
├── top.akizip.akizip.json     # Flatpak manifest
├── update-po.sh               # translation pipeline
└── meson.build
```

### Architecture in brief

- `AkizipApplication` is an `Adw.Application` singleton that owns three siblings: `app.commands` (a `"group.action" → callable` dictionary), `app.job_queue` (the background worker), and `app.system` (a `sysop()` instance holding the current selection state).
- **Immediate plugins** (`plugins/system.py`, `plugins/status.py`) are plain Python objects called synchronously by the UI. They must not block.
- **Long-running plugins** (`plugins/sevenzip.py`, `plugins/system_job.py`) expose a `register(commands)` function and submit work through `JobQueue`. Each callable accepts `timeout=-1` and `cancel_event=None`, polls the cancel event, and respects the deadline.
- The window template lives in `src/window.ui` and is bundled into a GResource at build time. Mixins in `src/ui/` compose the main window — `LogPanelMixin` owns a separate logs window, `InfoDialogMixin` builds the archive-info dialog.

For deeper guidance on extending the plugin system, see [`src/plugins/readme.md`](src/plugins/readme.md).

## License

Akizip is released under the **GNU General Public License v3.0 or later**. See [`COPYING`](COPYING) for the full text.

The bundled `7zz` binary is provided by the upstream [7-Zip project](https://www.7-zip.org/) (www.7-zip.org). Portions of the software may use code licensed under the GNU LGPL.

## Acknowledgements

- [7-Zip](https://www.7-zip.org/) — the open-source archive engine. 7-Zip is a trademark of Igor Pavlov. This project is not affiliated with or endorsed by the 7-Zip project.
- [GTK](https://www.gtk.org/) and [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) — the toolkit and design library. GTK is a trademark of the GNOME Foundation.
- [PyGObject](https://pygobject.readthedocs.io/) — Python bindings for GTK and friends.

*Akizip is an independent community project and is not affiliated with, endorsed by, or sponsored by the GNOME Project or the GNOME Foundation. GNOME and the GNOME logo are trademarks of the GNOME Foundation.*
