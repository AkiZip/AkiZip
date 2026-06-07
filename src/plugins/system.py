import shutil
import time
from pathlib import Path


FULL_FEATURE_SUFFIXES = {
    ".7z",
    ".zip",
    ".tar",
}

READ_ONLY_SUFFIXES = {
    ".rar",
    ".gz",
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".tar.zst",
    ".tzst",
    ".tgz",
    ".tbz2",
    ".txz",
    ".cpio",
    ".rpm",
    ".deb",
    ".jar",
    ".apk",
    ".msi",
    ".iso",
}

NO_PREVIEW_SUFFIXES = {
    ".bz2",
    ".xz",
    ".zst",
}

# Additional archive formats 7-Zip can open but are not fully verified for modification.
ARCHIVE_SUFFIXES = {
    ".7z", ".zip", ".rar", ".tar", ".gz", ".bz2", ".xz",
    ".tar.gz", ".tar.bz2", ".tar.xz",
    ".cab", ".iso", ".dmg", ".wim", ".swm", ".esd",
    ".arj", ".z", ".taz", ".lzh", ".lha",
    ".zst", ".tar.zst", ".tzst",
    ".tgz", ".tbz2", ".txz",
    ".cpio", ".rpm", ".deb",
    ".jar", ".apk", ".msi",
}


def archive_suffix(path):
    """Return the archive suffix for a path, handling multi-part extensions like .tar.gz."""
    suffixes = path.suffixes
    if len(suffixes) >= 2:
        combined = ''.join(suffixes[-2:]).lower()
        if combined in ('.tar.gz', '.tar.bz2', '.tar.xz', '.tar.zst'):
            return combined
    return suffixes[-1].lower() if suffixes else ''


class sysop:
    def __init__(self):
        self.display_path = ""
        self.selected = None
        self.destination_display_path = ""
        self.destination = None
        self.msg = ""
        self.success = False
        self.updated_at = time.time()
        self.is_nested = False
        self._temp_dirs = []
        self._discovered_suffixes = set()

    def _select_path(self, path, display_path=None):
        if path is None or str(path).strip() == "":
            return self._failed("No path selected")

        selected = Path(path).expanduser()
        if not selected.exists():
            return self._failed(f"Path not found: {selected}")
        if not selected.is_file() and not selected.is_dir():
            return self._failed(f"Not a file or folder: {selected}")

        self.selected = selected
        self.display_path = str(display_path or selected)
        self.success = True
        self.msg = f"Selected {selected.name}"
        self.updated_at = time.time()
        return self

    def select_by_input(self, path):
        return self._select_path(path)

    def select_by_fileview(self, path=None, display_path=None):
        if path is None:
            return self._failed("File view did not return a path")
        return self._select_path(path, display_path)

    def select_nested(self, path, temp_dir, display_path=None):
        self._temp_dirs.append(str(temp_dir))
        self.is_nested = True
        return self._select_path(path, display_path)

    def _select_destination(self, path, display_path=None):
        if path is None or str(path).strip() == "":
            return self._failed("No destination selected")

        destination = Path(path).expanduser()
        if not destination.exists():
            return self._failed(f"Destination not found: {destination}")
        if not destination.is_dir():
            return self._failed(f"Destination is not a folder: {destination}")

        self.destination = destination
        self.destination_display_path = str(display_path or destination)
        self.success = True
        self.msg = f"Selected destination {destination.name}"
        self.updated_at = time.time()
        return self

    def select_destination_by_input(self, path):
        return self._select_destination(path)

    def select_destination_by_fileview(self, path=None, display_path=None):
        if path is None:
            return self._failed("File view did not return a destination")
        return self._select_destination(path, display_path)

    def cleanup_temp_dirs(self):
        for temp_dir in self._temp_dirs:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
        self._temp_dirs.clear()

    def clear_selected(self):
        self.cleanup_temp_dirs()
        self.selected = None
        self.display_path = ""
        self.is_nested = False
        self._discovered_suffixes.clear()
        self.success = False
        self.msg = "Selection cleared"
        self.updated_at = time.time()
        return self

    def clear_destination(self):
        self.destination = None
        self.destination_display_path = ""
        self.success = False
        self.msg = "Destination cleared"
        self.updated_at = time.time()
        return self

    def selected_file(self):
        return self.selected

    def selected_path(self):
        if self.selected is None:
            return ""
        return self.display_path or str(self.selected)

    def operation_path(self):
        if self.selected is None:
            return ""
        return str(self.selected)

    def destination_path(self):
        if self.destination is None:
            return ""
        return self.destination_display_path or str(self.destination)

    def destination_operation_path(self):
        if self.destination is None:
            return ""
        return str(self.destination)

    def has_selected(self):
        return self.selected is not None and self.selected.exists()

    def has_destination(self):
        return self.destination is not None and self.destination.exists() and self.destination.is_dir()

    def is_file(self):
        return self.selected is not None and self.selected.is_file()

    def is_folder(self):
        return self.selected is not None and self.selected.is_dir()

    def is_archive(self):
        if not self.is_file():
            return False
        suffix = archive_suffix(self.selected)
        return suffix in ARCHIVE_SUFFIXES or suffix in self._discovered_suffixes

    def add_discovered_suffix(self, suffix):
        self._discovered_suffixes.add(suffix)

    def clear_discovered_suffixes(self):
        self._discovered_suffixes.clear()

    def format_category(self):
        if not self.is_archive():
            return None
        if self.is_nested:
            return 'nested'
        suffix = archive_suffix(self.selected)
        if suffix in FULL_FEATURE_SUFFIXES:
            return 'full'
        if suffix in READ_ONLY_SUFFIXES:
            return 'readonly'
        if suffix in NO_PREVIEW_SUFFIXES:
            return 'no_preview'
        return 'unverified'

    def can_modify(self):
        return self.is_archive() and not self.is_nested and archive_suffix(self.selected) in FULL_FEATURE_SUFFIXES

    def is_zip(self):
        return self.is_file() and archive_suffix(self.selected) == ".zip"

    def can_compress(self):
        return self.is_file() or self.is_folder()

    def can_extract(self):
        return self.is_archive()

    def info(self):
        if self.selected is None:
            return {
                "selected": False,
                "path": "",
                "display_path": "",
                "operation_path": "",
                "destination_path": self.destination_path(),
                "destination_operation_path": self.destination_operation_path(),
                "has_destination": self.has_destination(),
                "name": "",
                "kind": "",
                "size": 0,
                "is_file": False,
                "is_folder": False,
                "is_archive": False,
                "is_zip": False,
                "can_compress": False,
                "can_extract": False,
                "format_category": None,
                "can_modify": False,
                "is_nested": False,
                "msg": self.msg,
                "success": self.success,
                "updated_at": self.updated_at,
            }

        is_file = self.is_file()
        is_folder = self.is_folder()
        return {
            "selected": True,
            "path": self.display_path or str(self.selected),
            "display_path": self.display_path or str(self.selected),
            "operation_path": str(self.selected),
            "destination_path": self.destination_path(),
            "destination_operation_path": self.destination_operation_path(),
            "has_destination": self.has_destination(),
            "name": self.selected.name,
            "kind": "folder" if is_folder else "file",
            "size": self.selected.stat().st_size if is_file else 0,
            "is_file": is_file,
            "is_folder": is_folder,
            "is_archive": self.is_archive(),
            "is_zip": self.is_zip(),
            "can_compress": self.can_compress(),
            "can_extract": self.can_extract(),
            "format_category": self.format_category(),
            "can_modify": self.can_modify(),
            "is_nested": self.is_nested,
            "msg": self.msg,
            "success": self.success,
            "updated_at": self.updated_at,
        }

    def status(self):
        return self.info()

    def _failed(self, msg):
        self.success = False
        self.msg = msg
        self.updated_at = time.time()
        return self


System = sysop
