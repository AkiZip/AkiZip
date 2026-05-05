<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Akizip Logo" width="128" height="128" />

# Akizip

A modern GTK 4 / libadwaita front-end for 7-Zip, designed for the GNOME desktop.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)

</div>

---

## Screenshot

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Akizip Screenshot" />

</div>

## About

**Akizip** is a graphical archive utility that brings the power of [7-Zip](https://www.7-zip.org/) to the GNOME desktop through a clean, native interface built with GTK 4 and libadwaita. It is distributed as a Flatpak (`top.akizip.akizip`) and ships with a bundled `7zz` binary so you do not need to install 7-Zip separately.

Akizip is a **front-end**, not a library — it shells out to the bundled `7zz` executable for all archive work, ensuring full compatibility with the formats supported by upstream 7-Zip.

## Features

- **Native GNOME experience** — built with GTK 4 and libadwaita, following the GNOME Human Interface Guidelines.
- **Wide format support** — leverages 7-Zip for `.7z`, `.zip`, `.tar`, `.tar.gz`, `.gz`, `.rar` (read-only), and many more.
- **Compression and extraction** — create new archives or unpack existing ones with progress reporting.
- **Archive inspection** — view archive metadata and contents without extracting.
- **Cancellable, non-blocking jobs** — long-running operations run on a background worker thread and can be cancelled at any time.
- **Logs panel** — a dedicated, dockable window for inspecting command output and diagnostics.
- **Multilingual UI** — currently ships with English, Simplified Chinese (`zh_CN`), and Traditional Chinese (`zh_HK`) translations.
- **Sandboxed by default** — distributed as a Flatpak with minimal permissions.

## Installation

### Flatpak (recommended)

Build and install the Flatpak from the manifest:

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```


## Building from source

You will need `meson`, `ninja`, GTK 4 development headers, libadwaita development headers, PyGObject, and `gettext`.

```bash
meson setup build
meson compile -C build
meson test    -C build                              # validates desktop file, AppStream metainfo, GSettings schema
meson install -C build --destdir=/tmp/akizip-stage  # then run /tmp/akizip-stage/usr/local/bin/akizip
```

The launcher (`src/akizip.in`, becomes `build/src/akizip` after configuration) is the canonical entry point. Running `python3 -m akizip.main` directly from the source tree will **not** work, because the GResource bundle must be loaded first.

### Running on the host

`plugins/sevenzip.py` hard-codes the bundled binary path at `/app/bin/7zz`, which only exists inside the Flatpak sandbox. To run on the host, install `7zz` to that path (or symlink it), or temporarily edit the `SEVENZIP_PATH` constant.

## Translations

Translation work is driven by a small shell script, not by Meson:

```bash
./update-po.sh                              # extract strings into po/akizip.pot, msgmerge zh_CN.po and zh_HK.po
msgfmt --check po/zh_CN.po -o /dev/null     # validate a catalog without compiling
```

`po/POTFILES.in` lists the inputs. `update-po.sh` dispatches by extension: Python sources via `xgettext --language=Python`, `.ui` files via Glade, and `.desktop.in` / `.metainfo.xml.in` via the GNOME ITS file. Strings in `.gschema.xml` are listed but skipped from extraction (they are translated at runtime by GLib).

To add a new locale, append its code to `po/LINGUAS`, run `./update-po.sh`, and translate the generated `.po` file.

## Project layout

```
akizip/
├── data/                      # AppStream metainfo, .desktop, GSettings schema, icons
├── docs/                      # screenshots and design notes
├── po/                        # translation catalogs
├── src/
│   ├── akizip.in              # entry-point launcher (configured by meson)
│   ├── AkizipApplication.py   # Adw.Application singleton
│   ├── main.py                # process entry
│   ├── job_queue.py           # single-thread background worker
│   ├── window.py / window.ui  # main window
│   ├── plugins/               # state and long-running plugins
│   └── ui/                    # window mixins (logs, info dialog, ...)
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

The bundled `7zz` binary is provided by the upstream [7-Zip project](https://www.7-zip.org/) and is distributed under its own terms.

## Acknowledgements

- [7-Zip](https://www.7-zip.org/) — the archive engine that does the real work.
- [GTK](https://www.gtk.org/) and [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) — the toolkit and design library.
- [PyGObject](https://pygobject.readthedocs.io/) — Python bindings for GTK and friends.
