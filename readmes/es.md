<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Logotipo de Akizip" width="128" height="128" />

# Akizip

Un gestor de archivos comprimidos moderno para GNOME, creado con GTK 4 y libadwaita.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![Estado de traducción](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)
[![Blog](https://img.shields.io/badge/blog-akizip.top-orange.svg)](https://blog.akizip.top/)

**Idiomas:** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-HK.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

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
- **Interfaz multilingüe** — se distribuye con traducciones a más de 10 idiomas (incluidos inglés, chino, español, francés, italiano, ruso y más), contribuidas a través de [Weblate](https://hosted.weblate.org/engage/akizip/).
- **Aislado por defecto** — distribuido como Flatpak con permisos mínimos.

## Instalación

Akizip se distribuye exclusivamente como Flatpak. Compílalo e instálalo desde el manifiesto:

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```

## Traducciones

El trabajo de traducción lo controla un pequeño script shell, no Meson:

```bash
./update-po.sh                              # extrae cadenas a po/akizip.pot y ejecuta msgmerge sobre todos los catálogos de po/LINGUAS
msgfmt --check po/zh_CN.po -o /dev/null     # valida un catálogo sin compilarlo
```

`po/POTFILES.in` enumera las entradas. `update-po.sh` despacha según la extensión: fuentes Python mediante `xgettext --language=Python`, archivos `.ui` mediante Glade, y `.desktop.in` / `.metainfo.xml.in` mediante el archivo ITS de GNOME. Las cadenas en `.gschema.xml` se listan pero se omiten durante la extracción (GLib las traduce en tiempo de ejecución).

Para añadir una nueva configuración regional, agrega su código a `po/LINGUAS`, ejecuta `./update-po.sh` y traduce el archivo `.po` generado.

Las traducciones también pueden contribuirse a través de [Weblate](https://hosted.weblate.org/engage/akizip/).

## Estructura del proyecto

```
akizip/
├── data/                      # metadatos AppStream, .desktop, schema de GSettings, servicio D-Bus, iconos
├── docs/                      # capturas de pantalla y notas de diseño
├── po/                        # catálogos de traducción (POTFILES.in, LINGUAS, *.po)
├── readmes/                   # versiones localizadas de este README
├── scripts/                   # scripts auxiliares (p. ej., comprobación de formato)
├── src/
│   ├── akizip.in              # lanzador de entrada (configurado por meson)
│   ├── akizip.gresource.xml   # manifiesto GResource que empaqueta los archivos .ui
│   ├── AkizipApplication.py   # singleton Adw.Application
│   ├── main.py                # entrada del proceso
│   ├── job_queue.py           # trabajador en segundo plano de un solo hilo
│   ├── window.py / window.ui  # ventana principal
│   ├── *.ui                   # diálogos: añadir, comprimir, extraer, preferencias, atajos, selector de carpeta de destino
│   ├── plugins/               # plugins de estado y de larga ejecución (sevenzip, system, status, password, context_menu, ...)
│   └── ui/                    # mixins de ventana (panel de registros, diálogo de información, diálogo de añadir, ...)
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

*Akizip es un proyecto comunitario independiente y no está afiliado, respaldado ni patrocinado por el proyecto GNOME ni por la GNOME Foundation. GNOME y el logotipo de GNOME son marcas comerciales de la GNOME Foundation.*

---

*Este README ha sido traducido por IA. En caso de cualquier conflicto o discrepancia con la versión en inglés, prevalece la [versión en inglés](../README.md).*
