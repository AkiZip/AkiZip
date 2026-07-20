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
import signal
import subprocess
import threading
import time
from pathlib import Path


SEVENZIP_PATH = '/app/bin/7zz'


def _parse_progress(line):
    match = re.search(r'(\d+)%', line)
    if match:
        return int(match.group(1))
    return None


def _run_7zip(args, timeout=-1, cancel_event=None, on_progress=None):
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


def _run_7zip_stdin(args, stdin_path, timeout=-1, cancel_event=None, on_progress=None):
    if on_progress is not None:
        args = list(args) + ['-bsp2']

    started_at = time.monotonic()

    with open(stdin_path, 'rb') as stdin_file:
        process = subprocess.Popen(
            [SEVENZIP_PATH, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=stdin_file,
            start_new_session=True,
        )

        if on_progress is None:
            stdout_bytes, stderr_bytes = process.communicate()
            stdout = stdout_bytes.decode('utf-8', errors='replace')
            stderr = stderr_bytes.decode('utf-8', errors='replace')
            output = (stdout + '\n' + stderr).strip()
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
                        if char == b'\n':
                            stderr_lines.append(stderr_current)
                            stderr_current = ""
                        elif char == b'\x08':
                            stderr_current = stderr_current[:-1]
                        else:
                            stderr_current += char.decode('utf-8', errors='replace')
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
                    stdout_lines.append(line.decode('utf-8', errors='replace'))
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


def archive_add(archive_path, source_path, dest_folder='', password=None, timeout=-1, cancel_event=None, task_status=None):
    def on_progress(percent):
        if task_status is not None:
            task_status.set_progress(percent)

    source_path = Path(source_path)
    dest_folder = dest_folder.strip('/')

    if dest_folder:
        archive_name = str(Path(dest_folder) / source_path.name)
    else:
        archive_name = source_path.name

    args = ['a', str(archive_path), f'-si{archive_name}']
    if password:
        args.append(f'-p{password}')

    return _run_7zip_stdin(args, str(source_path), timeout, cancel_event, on_progress)


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
