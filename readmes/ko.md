<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Akizip 로고" width="128" height="128" />

# Akizip

GTK 4와 libadwaita로 만든 GNOME용 현대적인 아카이브 관리자입니다.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![번역 상태](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)

**언어:** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-HK.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

## 스크린샷

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Akizip 스크린샷" />

</div>

## 소개

**Akizip**은 GTK 4와 libadwaita로 만든 GNOME 데스크톱용 그래픽 아카이브 유틸리티입니다. Flatpak(`top.akizip.akizip`)으로 배포되며, 7z 및 기타 아카이브 형식을 처리하기 위한 `7zz` 바이너리를 함께 제공합니다.

Akizip은 라이브러리가 아니라 그래픽 애플리케이션입니다. 모든 아카이브 작업에 대해 함께 제공되는 `7zz` 실행 파일을 호출하며, 업스트림 7-Zip 엔진이 제공하는 형식을 지원합니다.

## 기능

- **네이티브 GNOME 경험** — GTK 4와 libadwaita로 만들었으며 GNOME 휴먼 인터페이스 가이드라인을 따릅니다.
- **폭넓은 형식 지원** — 함께 제공되는 7-Zip 엔진을 통해 `.7z`, `.zip`, `.tar`, `.tar.gz`, `.gz`, `.rar`(읽기 전용) 및 더 많은 형식을 지원합니다.
- **압축 및 추출** — 진행률 표시와 함께 새 아카이브를 만들거나 기존 아카이브를 풀 수 있습니다.
- **아카이브 검사** — 추출하지 않고 아카이브 메타데이터와 내용을 볼 수 있습니다.
- **취소 가능하고 비차단 방식의 작업** — 오래 실행되는 작업은 백그라운드 워커 스레드에서 실행되며 언제든지 취소할 수 있습니다.
- **로그 패널** — 명령 출력과 진단 정보를 확인하기 위한 전용 도킹 가능 창을 제공합니다.
- **다국어 UI** — 현재 영어, 중국어 간체(`zh_CN`), 중국어 번체(`zh_HK`) 번역을 함께 제공합니다.
- **기본 샌드박스 적용** — 최소 권한을 가진 Flatpak으로 배포됩니다.

## 설치

### Flatpak(권장)

매니페스트에서 Flatpak을 빌드하고 설치합니다.

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```


## 소스에서 빌드

`meson`, `ninja`, GTK 4 개발 헤더, libadwaita 개발 헤더, PyGObject, `gettext`가 필요합니다.

```bash
meson setup build
meson compile -C build
meson test    -C build                              # desktop 파일, AppStream 메타정보, GSettings schema 검증
meson install -C build --destdir=/tmp/akizip-stage  # 이후 /tmp/akizip-stage/usr/local/bin/akizip 실행
```

런처(`src/akizip.in`, 설정 후 `build/src/akizip`이 됨)가 표준 진입점입니다. GResource bundle을 먼저 로드해야 하므로 소스 트리에서 `python3 -m akizip.main`을 직접 실행하면 **동작하지 않습니다**.

### 호스트에서 실행

`plugins/sevenzip.py`는 함께 제공되는 바이너리 경로를 `/app/bin/7zz`로 하드코딩합니다. 이 경로는 Flatpak 샌드박스 안에만 존재합니다. 호스트에서 실행하려면 해당 경로에 `7zz`를 설치하거나 심볼릭 링크를 만들고, 또는 `SEVENZIP_PATH` 상수를 임시로 편집하세요.

## 번역

번역 작업은 Meson이 아니라 작은 shell 스크립트가 담당합니다.

```bash
./update-po.sh                              # 문자열을 po/akizip.pot으로 추출하고 zh_CN.po와 zh_HK.po를 msgmerge
msgfmt --check po/zh_CN.po -o /dev/null     # 컴파일하지 않고 카탈로그 검증
```

`po/POTFILES.in`은 입력 파일을 나열합니다. `update-po.sh`는 확장자별로 처리합니다. Python 소스는 `xgettext --language=Python`, `.ui` 파일은 Glade, `.desktop.in` / `.metainfo.xml.in` 파일은 GNOME ITS 파일을 사용합니다. `.gschema.xml`의 문자열은 목록에는 포함되지만 추출은 건너뜁니다(GLib이 런타임에 번역합니다).

새 로캘을 추가하려면 해당 코드를 `po/LINGUAS`에 추가하고 `./update-po.sh`를 실행한 다음 생성된 `.po` 파일을 번역하세요.

번역은 [Weblate](https://hosted.weblate.org/engage/akizip/)를 통해 기여할 수도 있습니다.

## 프로젝트 구조

```
akizip/
├── data/                      # AppStream 메타정보, .desktop, GSettings schema, 아이콘
├── docs/                      # 스크린샷 및 설계 노트
├── po/                        # 번역 카탈로그
├── src/
│   ├── akizip.in              # 진입점 런처(meson으로 설정)
│   ├── AkizipApplication.py   # Adw.Application 싱글턴
│   ├── main.py                # 프로세스 진입점
│   ├── job_queue.py           # 단일 스레드 백그라운드 워커
│   ├── window.py / window.ui  # 기본 창
│   ├── plugins/               # 상태 및 오래 실행되는 플러그인
│   └── ui/                    # 창 mixin(로그, 정보 대화상자 등)
├── top.akizip.akizip.json     # Flatpak 매니페스트
├── update-po.sh               # 번역 파이프라인
└── meson.build
```

### 아키텍처 요약

- `AkizipApplication`은 `Adw.Application` 싱글턴이며 세 개의 형제 객체를 소유합니다. `app.commands`(`"group.action" → callable` 딕셔너리), `app.job_queue`(백그라운드 워커), `app.system`(현재 선택 상태를 보관하는 `sysop()` 인스턴스)입니다.
- **즉시 실행 플러그인**(`plugins/system.py`, `plugins/status.py`)은 UI가 동기적으로 호출하는 일반 Python 객체입니다. 이들은 블로킹하면 안 됩니다.
- **오래 실행되는 플러그인**(`plugins/sevenzip.py`, `plugins/system_job.py`)은 `register(commands)` 함수를 노출하고 `JobQueue`를 통해 작업을 제출합니다. 각 callable은 `timeout=-1`과 `cancel_event=None`을 받고, 취소 이벤트를 폴링하며, 마감 시간을 지킵니다.
- 창 템플릿은 `src/window.ui`에 있으며 빌드 시 GResource로 번들됩니다. `src/ui/`의 mixin이 기본 창을 구성합니다. `LogPanelMixin`은 별도의 로그 창을 소유하고, `InfoDialogMixin`은 아카이브 정보 대화상자를 만듭니다.

플러그인 시스템 확장에 대한 자세한 안내는 [`src/plugins/readme.md`](../src/plugins/readme.md)를 참조하세요.

## 라이선스

Akizip은 **GNU General Public License v3.0 or later**로 배포됩니다. 전문은 [`COPYING`](../COPYING)을 참조하세요.

함께 제공되는 `7zz` 바이너리는 업스트림 [7-Zip 프로젝트](https://www.7-zip.org/)(www.7-zip.org)에서 제공합니다. 소프트웨어의 일부는 GNU LGPL 라이선스 코드가 사용될 수 있습니다.

## 감사의 말

- [7-Zip](https://www.7-zip.org/) — 오픈 소스 아카이브 엔진입니다. 7-Zip은 Igor Pavlov의 상표입니다. 이 프로젝트는 7-Zip 프로젝트와 제휴하거나 그 보증을 받지 않았습니다.
- [GTK](https://www.gtk.org/)와 [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) — 툴킷과 디자인 라이브러리입니다. GTK는 GNOME Foundation의 상표입니다.
- [PyGObject](https://pygobject.readthedocs.io/) — GTK 및 관련 구성 요소를 위한 Python 바인딩입니다.

*GNOME 및 GNOME 로고는 GNOME Foundation의 상표입니다.*
