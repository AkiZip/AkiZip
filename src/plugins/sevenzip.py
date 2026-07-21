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

_encoding_cache: dict[str, tuple[str, int | None]] = {}
_last_encoding: tuple[str, int | None] = ('utf-8', None)

# Map chardet encoding names → (our_encoding_name, mcp_value)
# Keys are normalised: lowercase, hyphens→underscores
_CHARDET_TO_MCP: dict[str, tuple[str, int | None]] = {
    'utf_8':         ('utf-8',      None),
    'ascii':         ('utf-8',      None),
    'gb2312':        ('gbk',        936),
    'gbk':           ('gbk',        936),
    'gb18030':       ('gbk',        936),
    'hz_gb_2312':    ('gbk',        936),
    'big5':          ('big5',       950),
    'big5hkscs':     ('big5',       950),
    'euc_tw':        ('big5',       950),
    'shift_jis':     ('shift_jis',  932),
    'euc_jp':        ('shift_jis',  932),
    'iso_2022_jp':   ('shift_jis',  932),
    'euc_kr':        ('euc_kr',     949),
    'iso_2022_kr':   ('euc_kr',     949),
    'cp949':         ('euc_kr',     949),
    'windows_1251':  ('cp1251',    1251),
    'koi8_r':        ('cp1251',    1251),
    'maccyrillic':   ('cp1251',    1251),
    'ibm855':        ('cp1251',    1251),
    'ibm866':        ('cp1251',    1251),
    'iso_8859_5':    ('cp1251',    1251),
}


def _parse_progress(line):
    match = re.search(r'(\d+)%', line)
    if match:
        return int(match.group(1))
    return None


def _detect_encoding(data: bytes) -> tuple[str, int | None]:
    if not data:
        return 'utf-8', None
    if not bytes(b for b in data if b > 127):
        return 'utf-8', None

    try:
        import chardet
        result = chardet.detect(data)
        enc_name = result.get('encoding', '')
        confidence = result.get('confidence', 0)
        if enc_name and confidence >= 0.4:
            key = enc_name.lower().replace('-', '_').replace(' ', '_')
            if key in _CHARDET_TO_MCP:
                return _CHARDET_TO_MCP[key]
    except ImportError:
        pass
    except Exception:
        pass

    try:
        utf8_decoded = data.decode('utf-8')
        if '\ufffd' not in utf8_decoded:
            return 'utf-8', None
    except UnicodeDecodeError:
        pass

    return _detect_encoding_fallback(data)


# Ordered preference for tie-breaking between CJK encodings
_CJK_PREFERENCE = {'gbk': 1, 'shift_jis': 0, 'big5': 0, 'euc_kr': 0}


# (encoding_name, mcp_codepage, is_multibyte) — fallback table
_FALLBACK_TABLE = [
    ('gbk',        936,     True),
    ('shift_jis',  932,     True),
    ('big5',       950,     True),
    ('euc_kr',     949,     True),
    ('cp1251',    1251,     False),
]


def _detect_encoding_fallback(data: bytes) -> tuple[str, int | None]:
    non_ascii_bytes = sum(1 for b in data if b > 127)

    multibyte = []
    singlebyte = []

    for enc, mcp, is_mb in _FALLBACK_TABLE:
        try:
            decoded = data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

        score = 0
        cjk = kana = hangul = cyr = 0
        for ch in decoded:
            cp = ord(ch)
            if cp == 0xFFFD:
                score -= 100
            elif cp < 32 and cp not in (9, 10, 13):
                score -= 50
            elif cp > 127:
                score += 2
                if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
                    cjk += 1
                elif 0x3040 <= cp <= 0x30FF:
                    kana += 1
                elif 0xAC00 <= cp <= 0xD7AF:
                    hangul += 1
                elif 0x0400 <= cp <= 0x04FF:
                    cyr += 1

        score += cjk * 8 + kana * 10 + hangul * 10 + cyr * 2

        non_ascii_chars = sum(1 for c in decoded if ord(c) > 127)
        if not non_ascii_chars:
            continue

        bpc = non_ascii_bytes / non_ascii_chars
        if is_mb and bpc >= 1.2:
            multibyte.append((score, enc, mcp))
        elif not is_mb and bpc < 1.5:
            singlebyte.append((score, enc, mcp))

    if multibyte:
        multibyte.sort(key=lambda x: (x[0], _CJK_PREFERENCE.get(x[1], 0)), reverse=True)
        return multibyte[0][1], multibyte[0][2]

    if singlebyte:
        singlebyte.sort(key=lambda x: x[0], reverse=True)
        return singlebyte[0][1], singlebyte[0][2]

    return 'utf-8', None


def _decode_7zip_output(data: bytes) -> str:
    global _last_encoding
    _last_encoding = _detect_encoding(data)
    return data.decode(_last_encoding[0], errors='replace')


def _codepage_args(archive_path: str) -> list:
    enc, mcp = _encoding_cache.get(str(archive_path), (None, None))
    if mcp is not None:
        return [f'-mcp={mcp}', '-sccUTF-8']
    return []


def _ensure_encoding_cache(archive_path: str, password: str | None = None):
    archive_path = str(archive_path)
    if archive_path in _encoding_cache:
        return
    args = ['l', '-slt', '-ba', archive_path]
    if password:
        args.append(f'-p{password}')
    process = subprocess.Popen(
        [SEVENZIP_PATH, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        stdout_bytes, _ = process.communicate(timeout=30)
        if process.returncode == 0:
            enc, mcp = _detect_encoding(stdout_bytes)
            _encoding_cache[archive_path] = (enc, mcp)
    except Exception:
        pass


def _run_7zip(args, timeout=-1, cancel_event=None, on_progress=None):
    if on_progress is not None:
        args = list(args) + ['-bsp2']

    started_at = time.monotonic()
    process = subprocess.Popen(
        [SEVENZIP_PATH, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

    if on_progress is None:
        while True:
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                if cancel_event is not None and cancel_event.is_set():
                    _kill_process(process)
                    stdout_bytes, stderr_bytes = process.communicate()
                    raise RuntimeError('Cancelled')

                if timeout is not None and timeout >= 0:
                    elapsed = time.monotonic() - started_at
                    if elapsed >= timeout:
                        _kill_process(process)
                        stdout_bytes, stderr_bytes = process.communicate()
                        raise TimeoutError(f'7zz timed out after {timeout} seconds')

        stdout = _decode_7zip_output(stdout_bytes)
        stderr = stderr_bytes.decode('utf-8', errors='replace')
        output = (stdout + '\n' + stderr).strip()
        if process.returncode != 0:
            raise RuntimeError(output or f'7zz exited with {process.returncode}')
        return output

    stderr_chunks = []
    stderr_current = b''
    stderr_lock = threading.Lock()
    last_percent = -1
    stdout_chunks = []

    def read_stderr():
        nonlocal stderr_current, last_percent
        while True:
            try:
                byte = process.stderr.read(1)
                if not byte:
                    break
                with stderr_lock:
                    if byte == b'\n':
                        stderr_chunks.append(stderr_current)
                        stderr_current = b''
                    elif byte == b'\x08':
                        stderr_current = stderr_current[:-1]
                    else:
                        stderr_current += byte
                    try:
                        current_text = stderr_current.decode('utf-8', errors='replace')
                    except Exception:
                        current_text = ''
                    percent = _parse_progress(current_text)
                    if percent is not None and percent != last_percent:
                        last_percent = percent
                        on_progress(percent)
            except Exception:
                break

    stderr_reader = threading.Thread(target=read_stderr, daemon=True)
    stderr_reader.start()

    def read_stdout():
        while True:
            try:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                stdout_chunks.append(chunk)
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

    stdout_bytes = b''.join(stdout_chunks)
    stdout = _decode_7zip_output(stdout_bytes)

    with stderr_lock:
        stderr = '\n'.join(
            [c.decode('utf-8', errors='replace') for c in stderr_chunks]
            + [stderr_current.decode('utf-8', errors='replace')]
        )

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
            stdout = _decode_7zip_output(stdout_bytes)
            stderr = stderr_bytes.decode('utf-8', errors='replace')
            output = (stdout + '\n' + stderr).strip()
            if process.returncode != 0:
                raise RuntimeError(output or f'7zz exited with {process.returncode}')
            return output

        stderr_chunks = []
        stderr_current = b''
        stderr_lock = threading.Lock()
        last_percent = -1
        stdout_chunks = []

        def read_stderr():
            nonlocal stderr_current, last_percent
            while True:
                try:
                    byte = process.stderr.read(1)
                    if not byte:
                        break
                    with stderr_lock:
                        if byte == b'\n':
                            stderr_chunks.append(stderr_current)
                            stderr_current = b''
                        elif byte == b'\x08':
                            stderr_current = stderr_current[:-1]
                        else:
                            stderr_current += byte
                        try:
                            current_text = stderr_current.decode('utf-8', errors='replace')
                        except Exception:
                            current_text = ''
                        percent = _parse_progress(current_text)
                        if percent is not None and percent != last_percent:
                            last_percent = percent
                            on_progress(percent)
                except Exception:
                    break

        stderr_reader = threading.Thread(target=read_stderr, daemon=True)
        stderr_reader.start()

        def read_stdout():
            while True:
                try:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        break
                    stdout_chunks.append(chunk)
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

        stdout_bytes = b''.join(stdout_chunks)
        stdout = _decode_7zip_output(stdout_bytes)

        with stderr_lock:
            stderr = '\n'.join(
                [c.decode('utf-8', errors='replace') for c in stderr_chunks]
                + [stderr_current.decode('utf-8', errors='replace')]
            )

        output = (stdout + '\n' + stderr).strip()
        if process.returncode != 0:
            raise RuntimeError(output or f'7zz exited with {process.returncode}')
        return output


def archive_info(archive_path, password=None, timeout=-1, cancel_event=None):
    args = ['l', '-slt', str(archive_path)]
    if password:
        args.append(f'-p{password}')
    output = _run_7zip(args, timeout, cancel_event)
    _encoding_cache[str(archive_path)] = _last_encoding
    return output


def archive_list(archive_path, password=None, timeout=-1, cancel_event=None):
    args = ['l', '-slt', '-ba', str(archive_path)]
    if password:
        args.append(f'-p{password}')
    output = _run_7zip(args, timeout, cancel_event)
    _encoding_cache[str(archive_path)] = _last_encoding
    return output


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

    if str(archive_path) not in _encoding_cache:
        _ensure_encoding_cache(archive_path, password)

    args = [
        'x',
        str(archive_path),
        f'-o{output_dir}',
        '-y',
        *_codepage_args(archive_path),
    ]
    if password:
        args.append(f'-p{password}')
    return _run_7zip(args, timeout, cancel_event, on_progress)


def archive_extract_FileInZip(archive_path, file_name, output_dir, password=None, timeout=-1, cancel_event=None, task_status=None):
    def on_progress(percent):
        if task_status is not None:
            task_status.set_progress(percent)

    if str(archive_path) not in _encoding_cache:
        _ensure_encoding_cache(archive_path, password)

    args = [
        'x',
        str(archive_path),
        f'-o{output_dir}',
        '-y',
        *_codepage_args(archive_path),
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
