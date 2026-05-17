# Usage:
# scanner(archive_path, maxThreads, sevenzipPath='/app/bin/7zz').call_scan(path=None, maxLevel=3)
# Returns {PurePosixPath: (is_file, name)} for paths inside archives.
# scanner(...).count_files(path=None, maxLevel=3) returns the number of files.
# scanner(...).scan_exist(archivePath, destinationPath) returns existing extract conflicts.
# maxThreads=-1 means no scanner-specific thread limit; maxLevel=-1 means unlimited path depth.
# Archive files inside the archive are recorded as folders, but they are not extracted or opened.

from collections import defaultdict
from pathlib import Path, PurePosixPath
import os
import random
import signal
import subprocess
import threading
import time

from .system import ARCHIVE_SUFFIXES, archive_suffix


SEVENZIP_PATH = '/app/bin/7zz'


class scanner():
    def __init__(self, basePath, maxThreads, sevenzipPath=SEVENZIP_PATH):
        self.basePath = Path(basePath).expanduser()
        self.sevenzipPath = sevenzipPath
        self.pathDict = defaultdict(dict)
        # {jobId: {archive_path: (True(is file), name), archive_path: (False(not file), name)}}
        if maxThreads == -1:
            self.maxThreads = float('inf')
        elif maxThreads <= 0:
            raise ValueError(f'gets maxThreads={maxThreads}, maxThreads needs be -1 or positive.')
        else:
            self.maxThreads = maxThreads
        self.jobs = defaultdict(int)
        self._lock = threading.Lock()

    def getCurThreads(self):
        return threading.active_count()

    def newJobId(self):
        ret = random.randint(1, 500)
        with self._lock:
            while ret in self.jobs:
                ret = random.randint(1, 500)
            self.jobs[ret] = 0
            self.pathDict[ret] = {}
        return ret

    def _add_job(self, jobId):
        with self._lock:
            self.jobs[jobId] += 1

    def _finish_job(self, jobId):
        with self._lock:
            self.jobs[jobId] -= 1

    def _get_job_count(self, jobId):
        with self._lock:
            return self.jobs[jobId]

    def _add_path(self, jobId, path, isFile):
        path = PurePosixPath(str(path).replace('\\', '/'))
        self.pathDict[jobId][path] = (isFile, path.name)

    def _kill_process(self, process):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def _run_7zip(self, args, timeout=-1):
        started_at = time.monotonic()
        process = subprocess.Popen(
            [self.sevenzipPath, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            start_new_session=True,
        )

        while True:
            try:
                stdout, stderr = process.communicate(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                if timeout is not None and timeout >= 0:
                    elapsed = time.monotonic() - started_at
                    if elapsed >= timeout:
                        self._kill_process(process)
                        stdout, stderr = process.communicate()
                        output = (stdout + stderr).strip()
                        raise TimeoutError(output or f'7zz timed out after {timeout} seconds')

        output = (stdout + stderr).strip()
        if process.returncode != 0:
            raise RuntimeError(output or f'7zz exited with {process.returncode}')
        return output

    def archive_list(self, archivePath, password=None, timeout=-1):
        args = ['l', '-slt', '-ba', str(archivePath)]
        if password:
            args.append(f'-p{password}')
        return self._run_7zip(args, timeout)

    def scan_path(self, path, levelLeft=3, jobId=0, counted=False, prefix=""):
        if not counted:
            self._add_job(jobId)
        try:
            self._scan_path(path, levelLeft, jobId, prefix)
        finally:
            self._finish_job(jobId)

    def _scan_path(self, path, levelLeft=3, jobId=0, prefix=""):
        path = Path(path).expanduser()
        if not path.exists() or not path.is_file():
            return

        archive_name = prefix.rstrip('/') or path.name
        self._add_path(jobId, archive_name, False)

        if levelLeft == 0:
            return

        try:
            entries = self._parse_archive_entries(self.archive_list(path))
        except Exception:
            return

        for entry in entries:
            entry_path = entry.get('Path', '').replace('\\', '/').strip('/')
            if not entry_path:
                continue

            isFolder = self._is_folder_entry(entry)
            isArchive = archive_suffix(PurePosixPath(entry_path)) in ARCHIVE_SUFFIXES
            self._add_entry_path(jobId, archive_name, entry_path, not (isFolder or isArchive), levelLeft)

    def _add_entry_path(self, jobId, archiveName, entryPath, isFile, maxLevel):
        parts = [part for part in entryPath.split('/') if part]
        if not parts:
            return

        current = PurePosixPath(archiveName)
        for index, part in enumerate(parts, 1):
            if maxLevel != -1 and index > maxLevel:
                return

            current = current / part
            isLast = index == len(parts)
            self._add_path(jobId, current, isFile if isLast else False)

    def _parse_archive_entries(self, output):
        entries = []
        for block in output.split('\n\n'):
            block = block.strip()
            if not block:
                continue
            entry = {}
            for line in block.splitlines():
                if ' = ' in line:
                    key, value = line.split(' = ', 1)
                    entry[key.strip()] = value.strip()
            if entry.get('Path'):
                entries.append(entry)
        return entries

    def _is_folder_entry(self, entry):
        return 'D' in entry.get('Attributes', '') or entry.get('Folder') == '+'

    def _build_entry_tree(self, entries):
        tree = {'folders': {}, 'files': {}}
        for entry in entries:
            entry_path = entry.get('Path', '').replace('\\', '/').strip('/')
            if not entry_path:
                continue

            parts = [part for part in entry_path.split('/') if part]
            if not parts:
                continue

            node = tree
            for part in parts[:-1]:
                node = node['folders'].setdefault(part, {'folders': {}, 'files': {}})

            name = parts[-1]
            if self._is_folder_entry(entry):
                node['folders'].setdefault(name, {'folders': {}, 'files': {}})
            else:
                node['files'][name] = entry
        return tree

    def _scan_exist_tree(self, node, destinationPath, archivePath, result):
        for fileName in node['files']:
            targetPath = destinationPath / fileName
            if targetPath.exists():
                result[archivePath / fileName] = (True, fileName)

        for folderName, childNode in node['folders'].items():
            targetPath = destinationPath / folderName
            if not targetPath.exists():
                continue

            childArchivePath = archivePath / folderName
            result[childArchivePath] = (False, folderName)
            self._scan_exist_tree(childNode, targetPath, childArchivePath, result)

    def scan_exist(self, archivePath=None, destinationPath=None):
        if archivePath is None:
            archivePath = self.basePath
        if destinationPath is None:
            raise ValueError('destinationPath is required')

        archivePath = Path(archivePath).expanduser()
        destinationPath = Path(destinationPath).expanduser()
        if not archivePath.exists() or not archivePath.is_file():
            return {}
        if not destinationPath.exists() or not destinationPath.is_dir():
            return {}

        try:
            entries = self._parse_archive_entries(self.archive_list(archivePath))
        except Exception:
            return {}

        tree = self._build_entry_tree(entries)
        result = {}
        self._scan_exist_tree(tree, destinationPath, PurePosixPath(''), result)
        return result

    def call_scan(self, path=None, maxLevel=3):
        if path is None:
            path = self.basePath

        jobId = self.newJobId()
        self.scan_path(path, maxLevel, jobId)
        while self._get_job_count(jobId) != 0:
            time.sleep(0.05)
            continue

        ret = self.pathDict[jobId]
        with self._lock:
            self.jobs.pop(jobId, None)
            self.pathDict.pop(jobId, None)
        return ret

    def count_files(self, path=None, maxLevel=3):
        scanResult = self.call_scan(path, maxLevel)
        return sum(1 for isFile, _name in scanResult.values() if isFile)
