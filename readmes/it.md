<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Logo di Akizip" width="128" height="128" />

# Akizip
Un gestore grafico di archivi 7-Zip per Linux

[![Licenza: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Piattaforma](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![Stato traduzione](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)
[![Blog](https://img.shields.io/badge/blog-akizip.top-orange.svg)](https://blog.akizip.top/)

**Lingue:** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-HK.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Schermata di Akizip" width="800" />

</div>

# Informazioni

### Introduzione

- Un gestore grafico di archivi 7-Zip per Linux.
- Realizzato con GTK 4 e libadwaita nel rispetto delle linee guida per l'interfaccia umana di GNOME.
- Distribuito come Flatpak, con accesso sicuro ai file scelti dall'utente tramite il selettore di file e con autorizzazioni ridotte per quanto possibile.

### Funzionalità

- **Formati supportati** — Consente di creare archivi `.7z`, `.zip` e `.tar`; estrarre `.rar`, `.gz`, `.bz2`, `.xz`, `.tar.gz`, `.tar.bz2`, `.tar.xz`, `.iso` e molti altri formati; permette inoltre di esplorare direttamente il contenuto della maggior parte dei formati supportati.
- **Suggerimenti intelligenti** — Suggerisce automaticamente i parametri dell'archivio in base alla composizione dei file sorgente.
- **Impostazioni di compressione** — Consente di regolare manualmente i parametri di compressione e il numero di thread; supporta la protezione con password e la crittografia dei nomi dei file 7z.
- **Gestione degli archivi** — Permette di visualizzare, creare, spostare ed eliminare file all'interno degli archivi senza estrarli, consultare l'elenco dei file e i metadati e aprire archivi nidificati.
- **Estrazione e verifica di integrità** — Consente di estrarre l'intero archivio o solo gli elementi selezionati, gestire archivi protetti da password e verificarne l'integrità prima dell'estrazione.
- **Attività in background** — Esegue le operazioni complesse in background con avanzamento in tempo reale, tempo residuo stimato, timeout configurabili e annullamento; il pannello dei registri consente di consultare l'output dei comandi e le informazioni diagnostiche.
- **Più lingue** — Offre l'interfaccia in oltre 10 lingue e permette di contribuire alle traduzioni tramite [Weblate](https://hosted.weblate.org/engage/akizip/).

### Installazione

- Akizip è distribuito esclusivamente come Flatpak. Compilalo e installalo dal manifesto:

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```
<br>


# Sviluppo

### Struttura del progetto

```
akizip/
├── data/                      # Metadati AppStream, .desktop, schema GSettings, servizio D-Bus e icone
├── docs/                      # Schermate e note di progettazione
├── po/                        # Cataloghi di traduzione (POTFILES.in, LINGUAS, *.po)
├── readmes/                   # Versioni tradotte di questo README
├── scripts/                   # Script di supporto, come i controlli di formato
├── src/
│   ├── akizip.in              # Avvio del punto di ingresso configurato da Meson
│   ├── akizip.gresource.xml   # Manifesto GResource che include i file .ui
│   ├── AkizipApplication.py   # Istanza singola di Adw.Application
│   ├── main.py                # Punto di ingresso del processo
│   ├── job_queue.py           # Worker in background a thread singolo
│   ├── window.py / window.ui  # Finestra principale
│   ├── *.ui                   # Finestre per aggiunta, compressione, estrazione, preferenze, scorciatoie e scelta cartella
│   ├── plugins/               # Plugin di stato e attività lunghe (sevenzip, system, status, password, context_menu, ecc.)
│   └── ui/                    # Mixin della finestra per registri, informazioni, aggiunta e altro
├── top.akizip.akizip.json     # Manifesto Flatpak
├── update-po.sh               # Flusso di traduzione
└── meson.build
```

### Panoramica dell'architettura

Akizip utilizza un'architettura basata su plugin composta da tre parti principali: l'interfaccia, una coda di attività e i plugin funzionali.

- **Interfaccia** — `src/window.ui` definisce la finestra principale, mentre `src/ui/` gestisce interazioni come l'elenco dei file, le finestre di dialogo e il pannello dei registri.
- **Gestione dell'applicazione** — `AkizipApplication` collega l'interfaccia alle diverse funzioni e tiene traccia del file selezionato, dei comandi disponibili e delle attività in background.
- **Attività in background** — `JobQueue` esegue in ordine e in background le operazioni che richiedono tempo, come compressione ed estrazione, mantenendo reattiva l'interfaccia e gestendo avanzamento, annullamento e timeout.
- **Plugin funzionali** — Ogni plugin registra le proprie funzioni come comandi dell'applicazione, che l'interfaccia richiama quando necessario. Ad esempio, `plugins/sevenzip.py` usa 7-Zip per le operazioni sugli archivi, mentre `plugins/system_job.py` gestisce la scansione dei file, i suggerimenti intelligenti di compressione e lo spostamento dei file.

In breve: l'utente avvia un'operazione nell'interfaccia → l'applicazione trova la funzione corrispondente → l'attività viene eseguita in background → avanzamento e risultati tornano all'interfaccia.

Per una guida più approfondita su come estendere il sistema di plugin, consulta [`src/plugins/readme.md`](../src/plugins/readme.md).

### Traduzioni

Per aggiungere una nuova impostazione locale, aggiungi il relativo codice a `po/LINGUAS`, esegui `./update-po.sh` e traduci il file `.po` generato.

Puoi contribuire alle traduzioni anche tramite [Weblate](https://hosted.weblate.org/engage/akizip/).

<br>


# Licenza e ringraziamenti

### Licenza

Akizip è distribuito secondo la **GNU General Public License v3.0 or later**. Consulta [`COPYING`](../COPYING) per il testo completo.

Il file binario `7zz` incluso è fornito dal progetto upstream [7-Zip](https://www.7-zip.org/) (www.7-zip.org). Alcune parti del software potrebbero usare codice con licenza GNU LGPL.

### Ringraziamenti

- [7-Zip](https://www.7-zip.org/) — il motore di archiviazione open source. 7-Zip è un marchio di Igor Pavlov. Questo progetto non è affiliato al progetto 7-Zip né è da esso approvato.
- [GTK](https://www.gtk.org/) e [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) — il toolkit e la libreria di progettazione. GTK è un marchio di GNOME Foundation.
- [PyGObject](https://pygobject.readthedocs.io/) — collegamenti Python per GTK e i componenti correlati.

### Avvisi

*Akizip è un progetto comunitario indipendente e non è affiliato, approvato o sponsorizzato da GNOME Project o GNOME Foundation. GNOME e il logo GNOME sono marchi di GNOME Foundation.*

*Questo README è stato tradotto dall'IA. In caso di conflitto o discrepanza con la versione inglese, prevale la [versione inglese](../README.md).*
