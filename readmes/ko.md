<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/data/icons/hicolor/scalable/apps/top.akizip.akizip.svg" alt="Akizip 로고" width="128" height="128" />

# Akizip
Linux용 7-Zip 그래픽 압축 파일 관리자

[![라이선스: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![플랫폼](https://img.shields.io/badge/platform-Linux-green.svg)](https://flatpak.org)
[![Flatpak](https://img.shields.io/badge/distribution-Flatpak-blueviolet.svg)](https://flatpak.org)
[![번역 상태](https://hosted.weblate.org/widget/akizip/akizip/svg-badge.svg)](https://hosted.weblate.org/engage/akizip/)
[![블로그](https://img.shields.io/badge/blog-akizip.top-orange.svg)](https://blog.akizip.top/)

**언어:** [English](../README.md) | [简体中文](zh-CN.md) | [繁體中文](zh-HK.md) | [日本語](ja.md) | [한국어](ko.md) | [Español](es.md) | [Italiano](it.md)

</div>

---

<div align="center">

<img src="https://raw.githubusercontent.com/AkiZip/AkiZip/refs/heads/master/docs/shotcut.png" alt="Akizip 스크린샷" width="800" />

</div>

# 소개

### 개요

- Linux용 7-Zip 그래픽 압축 파일 관리자입니다.
- GTK 4와 libadwaita로 제작되었으며 GNOME 휴먼 인터페이스 지침을 따릅니다.
- Flatpak으로 배포되며, 권한을 가능한 한 제한하면서 파일 선택기를 통해 사용자가 지정한 파일에 안전하게 접근합니다.

### 기능

- **형식 지원** — `.7z`, `.zip`, `.tar` 압축 파일을 만들 수 있습니다. `.rar`, `.gz`, `.bz2`, `.xz`, `.tar.gz`, `.tar.bz2`, `.tar.xz`, `.cab`, `.iso`, `.dmg`, `.wim`, `.arj`, `.lzh` 등 다양한 형식을 풀 수 있으며, 지원 형식 대부분의 내용을 바로 탐색할 수 있습니다.
- **스마트 추천** — 원본 파일의 구성에 따라 압축 파일 매개변수를 자동으로 추천합니다.
- **압축 설정** — 압축 매개변수와 스레드 수를 직접 조정할 수 있으며, 암호 보호와 7z 파일 이름 암호화를 지원합니다.
- **압축 파일 관리** — 압축을 풀지 않고 내부 파일을 보고, 만들고, 이동하고, 삭제할 수 있습니다. 파일 목록과 압축 파일 메타데이터를 확인하고 중첩된 압축 파일도 열 수 있습니다.
- **압축 해제 및 무결성 검사** — 전체 압축 파일 또는 선택한 항목만 풀 수 있고, 암호로 보호된 압축 파일을 지원하며, 압축 해제 전에 무결성을 검사할 수 있습니다.
- **백그라운드 작업** — 복잡한 작업을 백그라운드에서 실행하며 실시간 진행률, 예상 남은 시간, 시간 제한 설정, 취소 기능을 제공합니다. 로그 패널에서 명령 출력과 진단 정보를 확인할 수 있습니다.
- **다국어 지원** — 10개 이상의 언어로 인터페이스를 사용할 수 있으며 [Weblate](https://hosted.weblate.org/engage/akizip/)를 통해 번역에 참여할 수 있습니다.

### 설치

- Akizip은 Flatpak으로만 배포됩니다. 매니페스트에서 빌드하고 설치하세요.

```bash
flatpak-builder --user --install --force-clean build-flatpak top.akizip.akizip.json
flatpak run top.akizip.akizip
```
<br>


# 개발

### 프로젝트 구조

```
akizip/
├── data/                      # AppStream 메타데이터, .desktop, GSettings schema, D-Bus service, 아이콘
├── docs/                      # 스크린샷과 설계 설명
├── po/                        # 번역 카탈로그(POTFILES.in, LINGUAS, *.po)
├── readmes/                   # 이 README의 다국어 버전
├── scripts/                   # 형식 검사 등의 보조 스크립트
├── src/
│   ├── akizip.in              # Meson으로 설정되는 진입점 실행기
│   ├── akizip.gresource.xml   # .ui 파일을 묶는 GResource 매니페스트
│   ├── AkizipApplication.py   # Adw.Application 싱글턴
│   ├── main.py                # 프로세스 진입점
│   ├── job_queue.py           # 단일 스레드 백그라운드 작업자
│   ├── window.py / window.ui  # 기본 창
│   ├── *.ui                   # 추가, 압축, 해제, 환경 설정, 바로 가기, 폴더 선택 대화 상자
│   ├── plugins/               # 상태 및 장기 실행 플러그인(sevenzip, system, status, password, context_menu 등)
│   └── ui/                    # 로그 패널, 정보, 추가 대화 상자 등의 창 mixin
├── top.akizip.akizip.json     # Flatpak 매니페스트
├── update-po.sh               # 번역 작업 흐름
└── meson.build
```

### 아키텍처 개요

Akizip은 인터페이스, 작업 대기열, 기능 플러그인의 세 부분으로 구성된 플러그인 기반 아키텍처를 사용합니다.

- **인터페이스** — `src/window.ui`가 기본 창을 정의하고, `src/ui/`가 파일 목록, 대화 상자, 로그 패널 등의 상호 작용을 담당합니다.
- **애플리케이션 관리** — `AkizipApplication`이 인터페이스와 각 기능을 연결하고 현재 선택한 파일, 사용 가능한 명령, 백그라운드 작업을 관리합니다.
- **백그라운드 작업** — `JobQueue`가 압축과 해제처럼 시간이 오래 걸리는 작업을 백그라운드에서 차례로 실행해 인터페이스가 멈추지 않도록 하며 진행률, 취소, 시간 제한을 처리합니다.
- **기능 플러그인** — 각 플러그인은 기능을 애플리케이션 명령으로 등록하고 필요할 때 인터페이스에서 호출됩니다. 예를 들어 `plugins/sevenzip.py`는 7-Zip을 이용한 압축 파일 작업을 담당하고, `plugins/system_job.py`는 파일 검색, 스마트 압축 추천, 파일 이동을 담당합니다.

간단히 말하면 사용자가 인터페이스에서 작업 시작 → 애플리케이션이 해당 기능 검색 → 백그라운드에서 작업 실행 → 진행률과 결과를 인터페이스에 반환하는 흐름입니다.

플러그인 시스템 확장에 대한 자세한 내용은 [`src/plugins/readme.md`](../src/plugins/readme.md)를 참조하세요.

### 번역

새 로캘을 추가하려면 해당 코드를 `po/LINGUAS`에 추가하고 `./update-po.sh`를 실행한 다음 생성된 `.po` 파일을 번역하세요.

[Weblate](https://hosted.weblate.org/engage/akizip/)를 통해서도 번역에 참여할 수 있습니다.

<br>


# 라이선스 및 감사의 말

### 라이선스

Akizip은 **GNU General Public License v3.0 or later**에 따라 배포됩니다. 전체 내용은 [`COPYING`](../COPYING)을 참조하세요.

포함된 `7zz` 바이너리는 업스트림 [7-Zip 프로젝트](https://www.7-zip.org/)(www.7-zip.org)에서 제공합니다. 소프트웨어의 일부에는 GNU LGPL로 라이선스된 코드가 사용될 수 있습니다.

### 감사의 말

- [7-Zip](https://www.7-zip.org/) — 오픈 소스 압축 엔진입니다. 7-Zip은 Igor Pavlov의 상표입니다. 이 프로젝트는 7-Zip 프로젝트와 관련이 없으며 그 승인을 받지 않았습니다.
- [GTK](https://www.gtk.org/)와 [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) — 툴킷 및 디자인 라이브러리입니다. GTK는 GNOME Foundation의 상표입니다.
- [PyGObject](https://pygobject.readthedocs.io/) — GTK 및 관련 구성 요소용 Python 바인딩입니다.

### 관련 고지

*Akizip은 독립적인 커뮤니티 프로젝트이며 GNOME Project 또는 GNOME Foundation과 관련이 없고, 이들의 승인이나 후원을 받지 않았습니다. GNOME과 GNOME 로고는 GNOME Foundation의 상표입니다.*

*이 README는 AI로 번역되었습니다. 영어 버전과 충돌하거나 불일치하는 부분이 있는 경우 [영어 버전](../README.md)이 우선합니다.*
