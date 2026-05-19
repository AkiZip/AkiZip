import errno
import os
import shutil
import time
from pathlib import Path

from .scan_system import scanner


COPY_CHUNK_SIZE = 1024 * 1024
DEFAULT_SCAN_DEPTH = 3
DEFAULT_SCAN_THREADS = 4

COMPRESSED_SUFFIXES = {
    ".7z", ".zip", ".rar", ".gz", ".bz2", ".xz", ".zst", ".lz", ".lzma",
    ".cab", ".iso", ".dmg", ".apk", ".jar", ".war", ".deb", ".rpm",
}
MEDIA_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".avif", ".mp3",
    ".aac", ".ogg", ".opus", ".flac", ".wav", ".mp4", ".m4v", ".mkv",
    ".mov", ".avi", ".webm",
}
DOCUMENT_SUFFIXES = {
    ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".toml",
    ".ini", ".log", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt",
    ".pptx", ".odt", ".ods", ".odp",
}
CODE_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".c", ".cc", ".cpp", ".h",
    ".hpp", ".rs", ".go", ".java", ".kt", ".swift", ".rb", ".php",
    ".html", ".css", ".scss", ".sh", ".sql",
}


_scanner = scanner("", DEFAULT_SCAN_THREADS)


def _empty_scan_result(root, max_depth):
    return {
        "root": str(root),
        "max_depth": max_depth,
        "total": 0,
        "files": 0,
        "folders": 0,
        "total_size": 0,
        "largest_file": {"path": "", "size": 0},
        "extensions": {},
        "categories": {
            "compressed": {"count": 0, "size": 0},
            "media": {"count": 0, "size": 0},
            "documents": {"count": 0, "size": 0},
            "code": {"count": 0, "size": 0},
            "other": {"count": 0, "size": 0},
        },
        "size_buckets": {
            "small": {"count": 0, "size": 0},
            "medium": {"count": 0, "size": 0},
            "large": {"count": 0, "size": 0},
            "huge": {"count": 0, "size": 0},
        },
        "errors": [],
    }


def _deadline(timeout):
    if timeout is None or timeout < 0:
        return None
    return time.monotonic() + timeout


def _check_stop(deadline, cancel_event=None):
    if cancel_event is not None and cancel_event.is_set():
        raise RuntimeError("Cancelled")
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError("Move timed out")


def move_path(source_path, destination_dir, timeout=-1, cancel_event=None):
    source = Path(source_path).expanduser()
    destination = Path(destination_dir).expanduser()
    deadline = _deadline(timeout)

    _check_stop(deadline, cancel_event)
    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source}")
    if not destination.exists() or not destination.is_dir():
        raise NotADirectoryError(f"Destination is not a folder: {destination}")

    target = destination / source.name
    if target.exists():
        raise FileExistsError(f"Target already exists: {target}")
    if source == destination or source in destination.parents:
        raise ValueError("Cannot move a folder into itself")

    try:
        source.replace(target)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        _copy_path(source, target, deadline, cancel_event)
        _check_stop(deadline, cancel_event)
        _remove_source(source)

    return f"Moved {source.name} to {destination}"


def _copy_path(source, target, deadline, cancel_event=None):
    _check_stop(deadline, cancel_event)
    try:
        if source.is_symlink():
            os.symlink(os.readlink(source), target)
            return
        if source.is_dir():
            _copy_dir(source, target, deadline, cancel_event)
        else:
            _copy_file(source, target, deadline, cancel_event)
    except Exception:
        _remove_partial(target)
        raise


def _copy_dir(source, target, deadline, cancel_event=None):
    target.mkdir()
    shutil.copystat(source, target, follow_symlinks=False)
    for child in source.iterdir():
        _check_stop(deadline, cancel_event)
        _copy_path(child, target / child.name, deadline, cancel_event)


def _copy_file(source, target, deadline, cancel_event=None):
    with source.open("rb") as src, target.open("xb") as dst:
        while True:
            _check_stop(deadline, cancel_event)
            chunk = src.read(COPY_CHUNK_SIZE)
            if not chunk:
                break
            dst.write(chunk)
    shutil.copystat(source, target, follow_symlinks=False)


def _remove_source(source):
    if source.is_dir() and not source.is_symlink():
        shutil.rmtree(source)
    else:
        source.unlink()


def _remove_partial(target):
    if not target.exists() and not target.is_symlink():
        return
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target, ignore_errors=True)
    else:
        try:
            target.unlink()
        except FileNotFoundError:
            pass


def scan_fileAndFolder(path, n=DEFAULT_SCAN_DEPTH):
    root = Path(path).expanduser()
    try:
        max_depth = int(n)
        if max_depth < -1:
            max_depth = DEFAULT_SCAN_DEPTH
    except (TypeError, ValueError):
        max_depth = DEFAULT_SCAN_DEPTH

    fileCount = _empty_scan_result(root, max_depth)
    if not root.exists():
        fileCount["errors"].append(f"Path not found: {root}")
        return fileCount

    scanned_paths = _scanner.call_scan(root, max_depth)
    for scanned_path, value in scanned_paths.items():
        is_file = value[0]
        if is_file:
            _scan_add_file(fileCount, scanned_path)
        else:
            fileCount["folders"] += 1

    fileCount["total"] = fileCount["files"] + fileCount["folders"]
    return fileCount


def _scan_folder(fileCount, folder, depth, max_depth):
    if depth >= max_depth:
        return

    try:
        children = list(folder.iterdir())
    except OSError as error:
        fileCount["errors"].append(f"{folder}: {error}")
        return

    for child in children:
        try:
            if child.is_dir() and not child.is_symlink():
                fileCount["folders"] += 1
                _scan_folder(fileCount, child, depth + 1, max_depth)
            else:
                _scan_add_file(fileCount, child)
        except OSError as error:
            fileCount["errors"].append(f"{child}: {error}")


def _scan_add_file(fileCount, file_path):
    try:
        stat = file_path.stat()
    except OSError as error:
        fileCount["errors"].append(f"{file_path}: {error}")
        return

    size = stat.st_size
    suffix = file_path.suffix.lower() or "<none>"
    category = _file_category(suffix)
    bucket = _size_bucket(size)

    fileCount["files"] += 1
    fileCount["total"] = fileCount["files"] + fileCount["folders"]
    fileCount["total_size"] += size

    extension = fileCount["extensions"].setdefault(suffix, {"count": 0, "size": 0})
    extension["count"] += 1
    extension["size"] += size

    fileCount["categories"][category]["count"] += 1
    fileCount["categories"][category]["size"] += size
    fileCount["size_buckets"][bucket]["count"] += 1
    fileCount["size_buckets"][bucket]["size"] += size

    if size > fileCount["largest_file"]["size"]:
        fileCount["largest_file"] = {"path": str(file_path), "size": size}


def _file_category(suffix):
    if suffix in COMPRESSED_SUFFIXES:
        return "compressed"
    if suffix in MEDIA_SUFFIXES:
        return "media"
    if suffix in CODE_SUFFIXES:
        return "code"
    if suffix in DOCUMENT_SUFFIXES:
        return "documents"
    return "other"


def _size_bucket(size):
    if size < 128 * 1024:
        return "small"
    if size < 10 * 1024 * 1024:
        return "medium"
    if size < 100 * 1024 * 1024:
        return "large"
    return "huge"


def suggest_zip_paramiters(fileCount):
    total_size = fileCount.get("total_size", 0) or 0
    files = fileCount.get("files", fileCount.get("total", 0)) or 0
    categories = fileCount.get("categories", {})
    compressed_size = _category_size(categories, "compressed")
    media_size = _category_size(categories, "media")
    code_size = _category_size(categories, "code")
    document_size = _category_size(categories, "documents")
    already_packed_ratio = _ratio(compressed_size + media_size, total_size)
    text_like_ratio = _ratio(code_size + document_size, total_size)

    suggestion = {
        "format": "7z",
        "method": "LZMA2",
        "level": 5,
        "solid": False,
        "dictionary": "32m",
        "threads": "on",
        "sevenzip_args": ["-t7z", "-m0=lzma2", "-mx=5", "-md=32m", "-mmt=on"],
        "reason": [],
    }

    if files == 0:
        suggestion.update({
            "level": 0,
            "method": "store",
            "sevenzip_args": ["-tzip", "-mx=0"],
            "reason": ["No files were found in the scan result."],
        })
        return suggestion

    if already_packed_ratio >= 0.90 and files < 50:
        suggestion.update({
            "format": "tar",
            "level": 0,
            "method": "store",
            "dictionary": "none",
            "threads": "on",
            "sevenzip_args": ["-ttar"],
            "reason": [
                "Most data is already compressed and the file count is small.",
                "Tar store mode packages files without recompression.",
            ],
        })
        return suggestion

    if already_packed_ratio >= 0.70:
        suggestion.update({
            "format": "zip",
            "method": "store",
            "level": 0,
            "solid": False,
            "dictionary": "none",
            "sevenzip_args": ["-tzip", "-mx=0"],
            "reason": [
                "Most data is already compressed media or archive content.",
                "Store mode avoids wasting time recompressing files with little size gain.",
            ],
        })
        return suggestion

    if text_like_ratio >= 0.60:
        dictionary = "64m" if total_size < 1024 * 1024 * 1024 else "128m"
        suggestion.update({
            "level": 9,
            "solid": True,
            "dictionary": dictionary,
            "sevenzip_args": [
                "-t7z", "-m0=lzma2", "-mx=9", f"-md={dictionary}",
                "-ms=on", "-mmt=on",
            ],
            "reason": [
                "Most data is text, documents, or source files.",
                "High LZMA2 compression with solid mode usually gives the best ratio.",
            ],
        })
        return suggestion

    if files > 5000:
        suggestion.update({
            "level": 7,
            "solid": True,
            "dictionary": "64m",
            "sevenzip_args": ["-t7z", "-m0=lzma2", "-mx=7", "-md=64m", "-ms=on", "-mmt=on"],
            "reason": [
                "The scan found many files.",
                "Solid mode helps reduce repeated metadata and small-file overhead.",
            ],
        })
        return suggestion

    if total_size >= 2 * 1024 * 1024 * 1024:
        suggestion.update({
            "level": 3,
            "dictionary": "32m",
            "sevenzip_args": ["-t7z", "-m0=lzma2", "-mx=3", "-md=32m", "-mmt=on"],
            "reason": [
                "The input is very large.",
                "A moderate level keeps compression time and memory use under control.",
            ],
        })
        return suggestion

    suggestion["reason"] = [
        "The scan looks mixed.",
        "Balanced LZMA2 settings should give a useful ratio without being too slow.",
    ]
    return suggestion


def _category_size(categories, name):
    return categories.get(name, {}).get("size", 0) or 0


def _ratio(part, total):
    if total <= 0:
        return 0
    return part / total


def set_scan_threads(max_threads):
    _scanner.setMaxThreads(max_threads)
    return f"System scan threads set to {max_threads}"


def register(commands):
    commands["system.move"] = move_path
    commands["system.scan"] = scan_fileAndFolder
    commands["system.suggest_zip_paramiters"] = suggest_zip_paramiters
    commands["system.set_scan_threads"] = set_scan_threads
