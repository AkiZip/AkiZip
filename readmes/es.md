<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Logotipo de Akizip" width="128" height="128" />

# Akizip

Un gestor de archivos comprimidos moderno para GNOME, creado con GTK 4 y libadwaita.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)

**Idiomas:** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-TW.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

## Captura de pantalla

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Captura de pantalla de Akizip" />

</div>

## Acerca de

**Akizip** es una utilidad gráfica de archivos comprimidos para el escritorio GNOME, creada con GTK 4 y libadwaita. Se distribuye como Flatpak (`top.akizip.akizip`) e incluye un binario `7zz` integrado para gestionar 7z y otros formatos de archivo comprimido.

Akizip es una aplicación gráfica, no una biblioteca: delega todo el trabajo de archivo comprimido en el ejecutable `7zz` incluido y admite los formatos proporcionados por el motor 7-Zip original.

## Características

- **Experiencia GNOME nativa** — creada con GTK 4 y libadwaita, siguiendo las GNOME Human Interface Guidelines.
- **Amplio soporte de formatos** — `.7z`, `.zip`, `.tar`, `.tar.gz`, `.gz`, `.rar` (solo lectura) y muchos más mediante el motor 7-Zip incluido.
- **Compresión y extracción** — crea archivos comprimidos nuevos o descomprime los existentes con informes de progreso.
- **Inspección de archivos comprimidos** — consulta metadatos y contenido sin extraer.
- **Trabajos cancelables y no bloqueantes** — las operaciones largas se ejecutan en un hilo de trabajo en segundo plano y pueden cancelarse en cualquier momento.
- **Panel de registros** — una ventana dedicada y acoplable para revisar la salida de comandos y diagnósticos.
- **Interfaz multilingüe** — actualmente se distribuye con traducciones al inglés, chino simplificado (`zh_CN`) y chino tradicional (`zh_HK`).
- **Aislado por defecto** — distribuido como Flatpak con permisos mínimos.

## Instalación

### Flatpak (recomendado)

Compila e instala el Flatpak desde el manifiesto:

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```


## Compilar desde el código fuente

Necesitarás `meson`, `ninja`, las cabeceras de desarrollo de GTK 4, las cabeceras de desarrollo de libadwaita, PyGObject y `gettext`.

```bash
meson setup build
meson compile -C build
meson test    -C build                              # valida el archivo desktop, los metadatos AppStream y el schema de GSettings
meson install -C build --destdir=/tmp/akizip-stage  # luego ejecuta /tmp/akizip-stage/usr/local/bin/akizip
```

El lanzador (`src/akizip.in`, que se convierte en `build/src/akizip` después de la configuración) es el punto de entrada canónico. Ejecutar `python3 -m akizip.main` directamente desde el árbol de código fuente **no** funcionará, porque primero debe cargarse el GResource bundle.

### Ejecutar en el host

`plugins/sevenzip.py` fija la ruta del binario incluido en `/app/bin/7zz`, que solo existe dentro del sandbox de Flatpak. Para ejecutarlo en el host, instala `7zz` en esa ruta (o crea un enlace simbólico), o edita temporalmente la constante `SEVENZIP_PATH`.

## Traducciones

El trabajo de traducción lo controla un pequeño script shell, no Meson:

```bash
./update-po.sh                              # extrae cadenas a po/akizip.pot y ejecuta msgmerge sobre zh_CN.po y zh_HK.po
msgfmt --check po/zh_CN.po -o /dev/null     # valida un catálogo sin compilarlo
```

`po/POTFILES.in` enumera las entradas. `update-po.sh` despacha según la extensión: fuentes Python mediante `xgettext --language=Python`, archivos `.ui` mediante Glade, y `.desktop.in` / `.metainfo.xml.in` mediante el archivo ITS de GNOME. Las cadenas en `.gschema.xml` se listan pero se omiten durante la extracción (GLib las traduce en tiempo de ejecución).

Para añadir una nueva configuración regional, agrega su código a `po/LINGUAS`, ejecuta `./update-po.sh` y traduce el archivo `.po` generado.

## Estructura del proyecto

```
akizip/
├── data/                      # metadatos AppStream, .desktop, schema de GSettings, iconos
├── docs/                      # capturas de pantalla y notas de diseño
├── po/                        # catálogos de traducción
├── src/
│   ├── akizip.in              # lanzador de entrada (configurado por meson)
│   ├── AkizipApplication.py   # singleton Adw.Application
│   ├── main.py                # entrada del proceso
│   ├── job_queue.py           # trabajador en segundo plano de un solo hilo
│   ├── window.py / window.ui  # ventana principal
│   ├── plugins/               # plugins de estado y de larga ejecución
│   └── ui/                    # mixins de ventana (registros, diálogo de información, ...)
├── top.akizip.akizip.json     # manifiesto Flatpak
├── update-po.sh               # flujo de traducción
└── meson.build
```

### Arquitectura en breve

- `AkizipApplication` es un singleton `Adw.Application` que posee tres elementos hermanos: `app.commands` (un diccionario `"group.action" → callable`), `app.job_queue` (el trabajador en segundo plano) y `app.system` (una instancia `sysop()` que mantiene el estado de selección actual).
- Los **plugins inmediatos** (`plugins/system.py`, `plugins/status.py`) son objetos Python normales llamados de forma síncrona por la interfaz. No deben bloquear.
- Los **plugins de larga ejecución** (`plugins/sevenzip.py`, `plugins/system_job.py`) exponen una función `register(commands)` y envían trabajo mediante `JobQueue`. Cada callable acepta `timeout=-1` y `cancel_event=None`, consulta el evento de cancelación y respeta el plazo.
- La plantilla de ventana vive en `src/window.ui` y se empaqueta en un GResource durante la compilación. Los mixins en `src/ui/` componen la ventana principal: `LogPanelMixin` posee una ventana de registros separada, e `InfoDialogMixin` construye el diálogo de información del archivo comprimido.

Para una guía más detallada sobre cómo ampliar el sistema de plugins, consulta [`src/plugins/readme.md`](../src/plugins/readme.md).

## Licencia

Akizip se publica bajo la **GNU General Public License v3.0 or later**. Consulta [`COPYING`](../COPYING) para ver el texto completo.

El binario `7zz` incluido lo proporciona el proyecto original [7-Zip](https://www.7-zip.org/) (www.7-zip.org). Algunas partes del software pueden usar código con licencia GNU LGPL.

## Agradecimientos

- [7-Zip](https://www.7-zip.org/) — el motor de archivos comprimidos de código abierto. 7-Zip es una marca comercial de Igor Pavlov. Este proyecto no está afiliado al proyecto 7-Zip ni cuenta con su respaldo.
- [GTK](https://www.gtk.org/) y [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) — el toolkit y la biblioteca de diseño. GTK es una marca comercial de la GNOME Foundation.
- [PyGObject](https://pygobject.readthedocs.io/) — enlaces de Python para GTK y componentes relacionados.

*GNOME y el logotipo de GNOME son marcas comerciales de la GNOME Foundation.*
