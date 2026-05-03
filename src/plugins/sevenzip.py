import os
import signal
import subprocess
import time
from pathlib import Path


SEVENZIP_PATH = '/app/bin/7zz'


def _run_7zip(args, timeout=-1, cancel_event=None):
    started_at = time.monotonic()
    process = subprocess.Popen(
        [SEVENZIP_PATH, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    while True:
        try:
            stdout, stderr = process.communicate(timeout=0.1)
            break
        except subprocess.TimeoutExpired:
            if cancel_event is not None and cancel_event.is_set():
                _kill_process(process)
                stdout, stderr = process.communicate()
                output = (stdout + stderr).strip()
                raise RuntimeError(output or 'Cancelled')

            if timeout is not None and timeout >= 0:
                elapsed = time.monotonic() - started_at
                if elapsed >= timeout:
                    _kill_process(process)
                    stdout, stderr = process.communicate()
                    output = (stdout + stderr).strip()
                    raise TimeoutError(output or f'7zz timed out after {timeout} seconds')

    output = (stdout + stderr).strip()
    if process.returncode != 0:
        raise RuntimeError(output or f'7zz exited with {process.returncode}')
    return output


def _kill_process(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def archive_info(archive_path, timeout=-1, cancel_event=None):
    return _run_7zip(['l', '-slt', str(archive_path)], timeout, cancel_event)


def archive_list(archive_path, timeout=-1, cancel_event=None):
    return _run_7zip(['l', '-slt', '-ba', str(archive_path)], timeout, cancel_event)


def archive_compress(output_archive, source_paths, timeout=-1, cancel_event=None):
    if isinstance(source_paths, (str, Path)):
        source_paths = [source_paths]

    return _run_7zip([
        'a',
        str(output_archive),
        *[str(path) for path in source_paths],
    ], timeout, cancel_event)


def archive_compress_advance(output_archive, source_paths, args, timeout=-1, cancel_event=None):
    if isinstance(source_paths, (str, Path)):
        source_paths = [source_paths]
    if args is None:
        args = []
    if isinstance(args, dict):
        args = args.get('sevenzip_args', [])

    return _run_7zip([
        'a',
        *[str(arg) for arg in args],
        str(output_archive),
        *[str(path) for path in source_paths],
    ], timeout, cancel_event)


def archive_extract(archive_path, output_dir, timeout=-1, cancel_event=None):
    return _run_7zip([
        'x',
        str(archive_path),
        f'-o{output_dir}',
        '-y',
    ], timeout, cancel_event)

def archive_extract_FileInZip(archive_path, file_name, output_dir, timeout=-1, cancel_event=None):
    return _run_7zip([
        'x',
        str(archive_path),
        f'-o{output_dir}',
        '-y',
        '--',
        str(file_name),
    ], timeout, cancel_event)

def register(commands):
    commands['archive.info'] = archive_info
    commands['archive.list'] = archive_list
    commands['archive.compress'] = archive_compress
    commands['archive.compress_advance'] = archive_compress_advance
    commands['archive.extract'] = archive_extract
    commands['archive.extract_file'] = archive_extract_FileInZip
