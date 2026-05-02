import errno
import os
import shutil
import time
from pathlib import Path


COPY_CHUNK_SIZE = 1024 * 1024


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


def register(commands):
    commands["system.move"] = move_path
