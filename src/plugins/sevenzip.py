# sevenzip.py
#
# Copyright 2026 akizip
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path


SEVENZIP_PATH = '/app/bin/7zz'


def _parse_progress(line):
    match = re.search(r'(\d+)%', line)
    if match:
        return int(match.group(1))
    return None


def _run_7zip(args, timeout=-1, cancel_event=None, on_progress=None, cwd=None):
    if on_progress is not None:
        args = list(args)
        if '--' in args:
            args.insert(args.index('--'), '-bsp2')
        else:
            args.append('-bsp2')

    started_at = time.monotonic()
    process = subprocess.Popen(
        [SEVENZIP_PATH, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
        cwd=cwd,
    )

    if on_progress is None:
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

    stderr_lines = []
    stderr_current = ""
    stderr_lock = threading.Lock()
    last_percent = -1

    def read_stderr():
        nonlocal stderr_current, last_percent
        while True:
            try:
                char = process.stderr.read(1)
                if not char:
                    break
                with stderr_lock:
                    if char == '\n':
                        stderr_lines.append(stderr_current)
                        stderr_current = ""
                    elif char == '\x08':
                        stderr_current = stderr_current[:-1]
                    else:
                        stderr_current += char
                    percent = _parse_progress(stderr_current)
                    if percent is not None and percent != last_percent:
                        last_percent = percent
                        on_progress(percent)
            except Exception:
                break

    stderr_reader = threading.Thread(target=read_stderr, daemon=True)
    stderr_reader.start()

    stdout_lines = []

    def read_stdout():
        while True:
            try:
                line = process.stdout.readline()
                if not line:
                    break
                stdout_lines.append(line)
            except Exception:
                break

    stdout_reader = threading.Thread(target=read_stdout, daemon=True)
    stdout_reader.start()

    while process.poll() is None:
        if cancel_event is not None and cancel_event.is_set():
            _kill_process(process)
            stderr_reader.join(timeout=1.0)
            stdout_reader.join(timeout=1.0)
            raise RuntimeError('Cancelled')

        if timeout is not None and timeout >= 0:
            elapsed = time.monotonic() - started_at
            if elapsed >= timeout:
                _kill_process(process)
                stderr_reader.join(timeout=1.0)
                stdout_reader.join(timeout=1.0)
                raise TimeoutError(f'7zz timed out after {timeout} seconds')

        time.sleep(0.1)

    stderr_reader.join(timeout=1.0)
    stdout_reader.join(timeout=1.0)

    with stderr_lock:
        stderr = '\n'.join(stderr_lines + [stderr_current])
    stdout = ''.join(stdout_lines)

    output = (stdout + '\n' + stderr).strip()
    if process.returncode != 0:
        raise RuntimeError(output or f'7zz exited with {process.returncode}')
    return output


def _kill_process(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def archive_info(archive_path, password=None, timeout=-1, cancel_event=None):
    args = ['l', '-slt', str(archive_path)]
    if password:
        args.append(f'-p{password}')
    return _run_7zip(args, timeout, cancel_event)


def archive_list(archive_path, password=None, timeout=-1, cancel_event=None):
    args = ['l', '-slt', '-ba', str(archive_path)]
    if password:
        args.append(f'-p{password}')
    return _run_7zip(args, timeout, cancel_event)


def archive_compress_advance(output_archive, source_paths, args, timeout=-1, cancel_event=None, task_status=None):
    if isinstance(source_paths, (str, Path)):
        source_paths = [source_paths]
    if args is None:
        args = []
    if isinstance(args, dict):
        args = args.get('sevenzip_args', [])

    def on_progress(percent):
        if task_status is not None:
            task_status.set_progress(percent)

    return _run_7zip([
        'a',
        *[str(arg) for arg in args],
        str(output_archive),
        *[str(path) for path in source_paths],
    ], timeout, cancel_event, on_progress)


def archive_extract(archive_path, output_dir, password=None, timeout=-1, cancel_event=None, task_status=None):
    def on_progress(percent):
        if task_status is not None:
            task_status.set_progress(percent)

    args = [
        'x',
        str(archive_path),
        f'-o{output_dir}',
        '-y',
    ]
    if password:
        args.append(f'-p{password}')
    return _run_7zip(args, timeout, cancel_event, on_progress)

def archive_extract_FileInZip(archive_path, file_name, output_dir, password=None, timeout=-1, cancel_event=None, task_status=None):
    def on_progress(percent):
        if task_status is not None:
            task_status.set_progress(percent)

    args = [
        'x',
        str(archive_path),
        f'-o{output_dir}',
        '-y',
    ]
    if password:
        args.append(f'-p{password}')
    args.extend(['--', str(file_name)])
    return _run_7zip(args, timeout, cancel_event, on_progress)

def archive_delete(archive_path, file_names, password=None, timeout=-1, cancel_event=None, task_status=None):
    def on_progress(percent):
        if task_status is not None:
            task_status.set_progress(percent)

    if isinstance(file_names, (str, Path)):
        file_names = [file_names]
    args = [
        'd',
        str(archive_path),
        *[str(name) for name in file_names],
    ]
    if password:
        args.append(f'-p{password}')
    return _run_7zip(args, timeout, cancel_event, on_progress)


def archive_add(archive_path, source_paths, dest_folder='', password=None, timeout=-1, cancel_event=None, task_status=None):
    def on_progress(percent):
        if task_status is not None:
            task_status.set_progress(percent)

    if isinstance(source_paths, (str, Path)):
        source_paths = [source_paths]
    source_paths = [Path(p) for p in source_paths]
    if not source_paths:
        raise RuntimeError('No source items')

    dest_folder = str(dest_folder).strip('/')
    dest = Path(dest_folder)
    if dest.is_absolute() or '..' in dest.parts:
        raise RuntimeError('Invalid destination folder')

    # Stage every source item as a symlink inside a temp directory so 7z sees
    # the exact archive layout we want (dest_folder/name), then compress from
    # the temp directory. 7z dereferences the links and stores the contents.
    temp_dir = tempfile.mkdtemp(prefix='akizip-add-')
    try:
        staged_names = []
        used_names = set()
        for source in source_paths:
            if not source.exists():
                raise RuntimeError(f'Source does not exist: {source}')
            base_name = source.name
            name = base_name
            counter = 2
            while str(dest / name) in used_names:
                stem, suffix = os.path.splitext(base_name)
                name = f'{stem} ({counter}){suffix}'
                counter += 1
            used_names.add(str(dest / name))

            link_path = Path(temp_dir) / dest / name
            link_path.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(source, link_path)
            staged_names.append(str(dest / name) if dest_folder else name)

        args = ['a', str(archive_path), *staged_names]
        if password:
            args.append(f'-p{password}')

        return _run_7zip(args, timeout, cancel_event, on_progress, cwd=temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def archive_test(archive_path, password=None, timeout=-1, cancel_event=None, task_status=None):
    def on_progress(percent):
        if task_status is not None:
            task_status.set_progress(percent)

    args = [
        't',
        str(archive_path),
    ]
    if password:
        args.append(f'-p{password}')
    output = _run_7zip(args, timeout, cancel_event, on_progress)
    if 'Everything is Ok' not in output:
        raise RuntimeError(output or 'Test failed')
    return output


def archive_move(archive_path, src_name, dst_name, password=None, timeout=-1, cancel_event=None, task_status=None):
    def on_progress(percent):
        if task_status is not None:
            task_status.set_progress(percent)

    args = [
        'rn',
        str(archive_path),
        str(src_name),
        str(dst_name),
    ]
    if password:
        args.append(f'-p{password}')
    return _run_7zip(args, timeout, cancel_event, on_progress)


def archive_rename(archive_path, src_name, new_name, password=None, timeout=-1, cancel_event=None, task_status=None):
    def on_progress(percent):
        if task_status is not None:
            task_status.set_progress(percent)

    src_name = str(src_name).strip('/')
    new_name = str(new_name).strip().strip('/')
    if not src_name:
        raise RuntimeError('Empty source name')
    if not new_name or '/' in new_name or new_name in ('.', '..'):
        raise RuntimeError('Invalid new name')

    parent = src_name.rpartition('/')[0]
    dst_name = parent + '/' + new_name if parent else new_name

    args = [
        'rn',
        str(archive_path),
        src_name,
        dst_name,
    ]
    if password:
        args.append(f'-p{password}')
    return _run_7zip(args, timeout, cancel_event, on_progress)


def archive_mkdir(archive_path, folder_path, password=None, timeout=-1, cancel_event=None, task_status=None):
    def on_progress(percent):
        if task_status is not None:
            task_status.set_progress(percent)

    folder_path = str(folder_path).strip('/')
    if not folder_path:
        raise RuntimeError('Empty folder name')

    folder = Path(folder_path)
    if folder.is_absolute() or '..' in folder.parts:
        raise RuntimeError('Invalid folder name')

    temp_dir = tempfile.mkdtemp(prefix='akizip-mkdir-')
    try:
        staged = Path(temp_dir) / folder
        staged.mkdir(parents=True)
        args = ['a', str(archive_path), folder_path]
        if password:
            args.append(f'-p{password}')
        return _run_7zip(args, timeout, cancel_event, on_progress, cwd=temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def register(commands):
    commands['archive.info'] = archive_info
    commands['archive.list'] = archive_list
    commands['archive.compress_advance'] = archive_compress_advance
    commands['archive.extract'] = archive_extract
    commands['archive.extract_file'] = archive_extract_FileInZip
    commands['archive.delete'] = archive_delete
    commands['archive.add'] = archive_add
    commands['archive.test'] = archive_test
    commands['archive.move'] = archive_move
    commands['archive.rename'] = archive_rename
    commands['archive.mkdir'] = archive_mkdir
