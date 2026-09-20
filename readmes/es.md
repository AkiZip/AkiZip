<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Logotipo de Akizip" width="128" height="128" />

# Akizip
Un gestor gráfico de archivos 7-Zip para Linux

[![Licencia: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Plataforma](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![Estado de traducción](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)
[![Blog](https://img.shields.io/badge/blog-akizip.top-orange.svg)](https://blog.akizip.top/)

**Idiomas:** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-HK.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Captura de pantalla de Akizip" width="800" />

</div>

# Acerca de

### Introducción

- Un gestor gráfico de archivos 7-Zip para Linux.
- Creado con GTK 4 y libadwaita de acuerdo con las directrices de interfaz humana de GNOME.
- Distribuido como Flatpak, con acceso seguro a los archivos elegidos por el usuario mediante el selector de archivos y con los permisos reducidos al mínimo posible.

### Características

- **Compatibilidad de formatos** — Permite crear archivos `.7z`, `.zip` y `.tar`; extraer `.rar`, `.gz`, `.bz2`, `.xz`, `.tar.gz`, `.tar.bz2`, `.tar.xz`, `.cab`, `.iso`, `.dmg`, `.wim`, `.arj`, `.lzh` y muchos otros formatos; y explorar directamente el contenido de la mayoría de los formatos compatibles.
- **Recomendaciones inteligentes** — Recomienda automáticamente los parámetros del archivo según la composición de los archivos de origen.
- **Ajustes de compresión** — Permite ajustar manualmente los parámetros de compresión y el número de hilos; admite protección con contraseña y cifrado de nombres de archivo en 7z.
- **Gestión de archivos comprimidos** — Permite ver, crear, mover y eliminar archivos dentro de un archivo comprimido sin extraerlo, consultar la lista de archivos y los metadatos, y abrir archivos comprimidos anidados.
- **Extracción y prueba de integridad** — Permite extraer todo el archivo o solo los elementos seleccionados, trabajar con archivos protegidos por contraseña y comprobar su integridad antes de extraerlos.
- **Tareas en segundo plano** — Ejecuta las operaciones complejas en segundo plano con progreso en tiempo real, tiempo restante estimado, límites de tiempo configurables y cancelación; el panel de registros permite consultar la salida de los comandos y la información de diagnóstico.
- **Varios idiomas** — Ofrece la interfaz en más de 10 idiomas y permite colaborar con las traducciones mediante [Weblate](https://hosted.weblate.org/engage/akizip/).

### Instalación

- Akizip se distribuye exclusivamente como Flatpak. Compílalo e instálalo desde el manifiesto:

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```
<br>


# Desarrollo

### Estructura del proyecto

```
akizip/
├── data/                      # Metadatos AppStream, .desktop, esquema GSettings, servicio D-Bus e iconos
├── docs/                      # Capturas de pantalla y notas de diseño
├── po/                        # Catálogos de traducción (POTFILES.in, LINGUAS, *.po)
├── readmes/                   # Versiones traducidas de este README
├── scripts/                   # Scripts auxiliares, como comprobaciones de formato
├── src/
│   ├── akizip.in              # Lanzador del punto de entrada configurado por Meson
│   ├── akizip.gresource.xml   # Manifiesto GResource que empaqueta los archivos .ui
│   ├── AkizipApplication.py   # Instancia única de Adw.Application
│   ├── main.py                # Punto de entrada del proceso
│   ├── job_queue.py           # Trabajador en segundo plano de un solo hilo
│   ├── window.py / window.ui  # Ventana principal
│   ├── *.ui                   # Diálogos para añadir, comprimir, extraer, preferencias, atajos y selección de carpetas
│   ├── plugins/               # Complementos de estado y tareas largas (sevenzip, system, status, password, context_menu, etc.)
│   └── ui/                    # Mixins de ventana para registros, información, diálogo de adición y más
├── top.akizip.akizip.json     # Manifiesto Flatpak
├── update-po.sh               # Flujo de trabajo de traducción
└── meson.build
```

### Resumen de la arquitectura

Akizip utiliza una arquitectura basada en complementos compuesta por tres partes principales: la interfaz, una cola de tareas y los complementos funcionales.

- **Interfaz** — `src/window.ui` define la ventana principal y `src/ui/` gestiona interacciones como la lista de archivos, los diálogos y el panel de registros.
- **Gestión de la aplicación** — `AkizipApplication` conecta la interfaz con las distintas funciones y mantiene el archivo seleccionado, los comandos disponibles y las tareas en segundo plano.
- **Tareas en segundo plano** — `JobQueue` ejecuta en orden y en segundo plano las operaciones que requieren tiempo, como la compresión y la extracción, para mantener la interfaz fluida mientras gestiona el progreso, la cancelación y los límites de tiempo.
- **Complementos funcionales** — Cada complemento registra sus funciones como comandos de la aplicación para que la interfaz los invoque cuando sea necesario. Por ejemplo, `plugins/sevenzip.py` usa 7-Zip para las operaciones con archivos, mientras que `plugins/system_job.py` se ocupa del análisis de archivos, las recomendaciones inteligentes de compresión y el movimiento de archivos.

En resumen: el usuario inicia una operación en la interfaz → la aplicación encuentra la función correspondiente → la tarea se ejecuta en segundo plano → el progreso y los resultados vuelven a la interfaz.

Para obtener una guía más detallada sobre cómo ampliar el sistema de complementos, consulta [`src/plugins/readme.md`](../src/plugins/readme.md).

### Traducciones

Para añadir una configuración regional, agrega su código a `po/LINGUAS`, ejecuta `./update-po.sh` y traduce el archivo `.po` generado.

También puedes colaborar con las traducciones mediante [Weblate](https://hosted.weblate.org/engage/akizip/).

<br>


# Licencia y agradecimientos

### Licencia

Akizip se publica bajo la **GNU General Public License v3.0 or later**. Consulta [`COPYING`](../COPYING) para leer el texto completo.

El binario `7zz` incluido es proporcionado por el proyecto original [7-Zip](https://www.7-zip.org/) (www.7-zip.org). Algunas partes del software pueden utilizar código con licencia GNU LGPL.

### Agradecimientos

- [7-Zip](https://www.7-zip.org/) — el motor de archivado de código abierto. 7-Zip es una marca comercial de Igor Pavlov. Este proyecto no está afiliado al proyecto 7-Zip ni cuenta con su respaldo.
- [GTK](https://www.gtk.org/) y [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) — el kit de herramientas y la biblioteca de diseño. GTK es una marca comercial de GNOME Foundation.
- [PyGObject](https://pygobject.readthedocs.io/) — enlaces de Python para GTK y componentes relacionados.

### Avisos

*Akizip es un proyecto comunitario independiente y no está afiliado, respaldado ni patrocinado por GNOME Project o GNOME Foundation. GNOME y el logotipo de GNOME son marcas comerciales de GNOME Foundation.*

*Este README ha sido traducido por IA. En caso de cualquier conflicto o discrepancia con la versión en inglés, prevalece la [versión en inglés](../README.md).*
