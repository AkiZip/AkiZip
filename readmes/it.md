<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Logo di Akizip" width="128" height="128" />

# Akizip

Un moderno gestore di archivi per GNOME, realizzato con GTK 4 e libadwaita.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![Stato della traduzione](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)

**Lingue:** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-HK.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

## Schermata

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Schermata di Akizip" />

</div>

## Informazioni

**Akizip** è un'utilità grafica per archivi destinata al desktop GNOME, realizzata con GTK 4 e libadwaita. È distribuita come Flatpak (`top.akizip.akizip`) e include un binario `7zz` integrato per gestire 7z e altri formati di archivio.

Akizip è un'applicazione grafica, non una libreria: per tutte le operazioni sugli archivi richiama l'eseguibile `7zz` incluso e supporta i formati forniti dal motore 7-Zip originale.

## Funzionalità

- **Esperienza GNOME nativa** — realizzata con GTK 4 e libadwaita, seguendo le GNOME Human Interface Guidelines.
- **Ampio supporto dei formati** — `.7z`, `.zip`, `.tar`, `.tar.gz`, `.gz`, `.rar` (sola lettura) e molti altri tramite il motore 7-Zip incluso.
- **Compressione ed estrazione** — crea nuovi archivi o estrae quelli esistenti con indicazione dell'avanzamento.
- **Ispezione degli archivi** — visualizza metadati e contenuti dell'archivio senza estrarre.
- **Operazioni annullabili e non bloccanti** — le operazioni lunghe vengono eseguite in un thread di lavoro in background e possono essere annullate in qualsiasi momento.
- **Pannello dei log** — una finestra dedicata e agganciabile per ispezionare output dei comandi e diagnostica.
- **Interfaccia multilingue** — attualmente include traduzioni in inglese, cinese semplificato (`zh_CN`) e cinese tradizionale (`zh_HK`).
- **Sandbox per impostazione predefinita** — distribuita come Flatpak con permessi minimi.

## Installazione

### Flatpak (consigliato)

Compila e installa il Flatpak dal manifest:

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```


## Compilazione dal sorgente

Ti serviranno `meson`, `ninja`, gli header di sviluppo di GTK 4, gli header di sviluppo di libadwaita, PyGObject e `gettext`.

```bash
meson setup build
meson compile -C build
meson test    -C build                              # valida il file desktop, i metadati AppStream e lo schema GSettings
meson install -C build --destdir=/tmp/akizip-stage  # poi esegui /tmp/akizip-stage/usr/local/bin/akizip
```

Il launcher (`src/akizip.in`, che diventa `build/src/akizip` dopo la configurazione) è il punto di ingresso canonico. Eseguire `python3 -m akizip.main` direttamente dall'albero sorgente **non** funzionerà, perché il GResource bundle deve essere caricato prima.

### Esecuzione sull'host

`plugins/sevenzip.py` definisce in modo fisso il percorso del binario incluso come `/app/bin/7zz`, che esiste solo all'interno della sandbox Flatpak. Per eseguirlo sull'host, installa `7zz` in quel percorso (o crea un collegamento simbolico), oppure modifica temporaneamente la costante `SEVENZIP_PATH`.

## Traduzioni

Il lavoro di traduzione è gestito da un piccolo script shell, non da Meson:

```bash
./update-po.sh                              # estrae le stringhe in po/akizip.pot ed esegue msgmerge su zh_CN.po e zh_HK.po
msgfmt --check po/zh_CN.po -o /dev/null     # valida un catalogo senza compilarlo
```

`po/POTFILES.in` elenca gli input. `update-po.sh` smista in base all'estensione: sorgenti Python tramite `xgettext --language=Python`, file `.ui` tramite Glade e `.desktop.in` / `.metainfo.xml.in` tramite il file ITS di GNOME. Le stringhe in `.gschema.xml` sono elencate ma saltate durante l'estrazione (vengono tradotte a runtime da GLib).

Per aggiungere una nuova lingua, aggiungi il relativo codice a `po/LINGUAS`, esegui `./update-po.sh` e traduci il file `.po` generato.

Le traduzioni possono essere contribuite anche tramite [Weblate](https://hosted.weblate.org/engage/akizip/).

## Struttura del progetto

```
akizip/
├── data/                      # metadati AppStream, .desktop, schema GSettings, icone
├── docs/                      # schermate e note di progettazione
├── po/                        # cataloghi di traduzione
├── src/
│   ├── akizip.in              # launcher di ingresso (configurato da meson)
│   ├── AkizipApplication.py   # singleton Adw.Application
│   ├── main.py                # ingresso del processo
│   ├── job_queue.py           # worker in background a singolo thread
│   ├── window.py / window.ui  # finestra principale
│   ├── plugins/               # plugin di stato e di lunga durata
│   └── ui/                    # mixin della finestra (log, dialogo informazioni, ...)
├── top.akizip.akizip.json     # manifest Flatpak
├── update-po.sh               # pipeline di traduzione
└── meson.build
```

### Architettura in breve

- `AkizipApplication` è un singleton `Adw.Application` che possiede tre elementi fratelli: `app.commands` (un dizionario `"group.action" → callable`), `app.job_queue` (il worker in background) e `app.system` (un'istanza `sysop()` che conserva lo stato della selezione corrente).
- I **plugin immediati** (`plugins/system.py`, `plugins/status.py`) sono normali oggetti Python chiamati in modo sincrono dall'interfaccia. Non devono bloccare.
- I **plugin di lunga durata** (`plugins/sevenzip.py`, `plugins/system_job.py`) espongono una funzione `register(commands)` e inviano lavoro tramite `JobQueue`. Ogni callable accetta `timeout=-1` e `cancel_event=None`, controlla periodicamente l'evento di annullamento e rispetta la scadenza.
- Il template della finestra si trova in `src/window.ui` ed è incluso in un GResource in fase di build. I mixin in `src/ui/` compongono la finestra principale: `LogPanelMixin` possiede una finestra log separata, mentre `InfoDialogMixin` costruisce il dialogo informazioni sull'archivio.

Per indicazioni più approfondite sull'estensione del sistema di plugin, consulta [`src/plugins/readme.md`](../src/plugins/readme.md).

## Licenza

Akizip è rilasciato sotto la **GNU General Public License v3.0 or later**. Consulta [`COPYING`](../COPYING) per il testo completo.

Il binario `7zz` incluso è fornito dal progetto originale [7-Zip](https://www.7-zip.org/) (www.7-zip.org). Parti del software possono usare codice con licenza GNU LGPL.

## Ringraziamenti

- [7-Zip](https://www.7-zip.org/) — il motore di archiviazione open source. 7-Zip è un marchio commerciale di Igor Pavlov. Questo progetto non è affiliato al progetto 7-Zip né approvato da esso.
- [GTK](https://www.gtk.org/) e [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) — il toolkit e la libreria di design. GTK è un marchio commerciale della GNOME Foundation.
- [PyGObject](https://pygobject.readthedocs.io/) — binding Python per GTK e componenti correlati.

*GNOME e il logo GNOME sono marchi commerciali della GNOME Foundation.*
