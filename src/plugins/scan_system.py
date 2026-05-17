# Usage:
# scanner(path, maxThreads=4).call_scan(path=None, maxLevel=3)
# Returns {Path: (is_file, name)} for filesystem paths.
# Use maxThreads=4 for normal scans.
# maxThreads=-1 means no scanner-specific thread limit and should only be used for controlled tests.
# maxLevel=-1 means unlimited depth.

from collections import defaultdict
from pathlib import Path
import random
import threading
import time


class scanner():
    def __init__(self, basePath, maxThreads):
        self.basePath = Path(basePath).expanduser()
        self.pathDict = defaultdict(dict)
        # {jobId: {path: (True(is file), name), path: (False(not file), name)}}
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
        self.pathDict[jobId][path.resolve()] = (isFile, path.name)

    def scan_path(self, path, levelLeft=3, jobId=0, counted=False):
        if not counted:
            self._add_job(jobId)
        try:
            self._scan_path(path, levelLeft, jobId)
        finally:
            self._finish_job(jobId)

    def _scan_path(self, path, levelLeft=3, jobId=0):
        path = Path(path).expanduser()

        if not path.exists():
            return

        if path.is_file() or path.is_symlink():
            self._add_path(jobId, path, True)
            return

        self._add_path(jobId, path, False)

        if levelLeft == 0:
            return

        if levelLeft != -1:
            nextLevel = levelLeft - 1
        else:
            nextLevel = -1

        try:
            children = list(path.iterdir())
        except OSError:
            return

        folders = []
        files = []
        for child in children:
            try:
                if child.is_dir() and not child.is_symlink():
                    folders.append(child)
                else:
                    files.append(child)
            except OSError:
                continue

        for file in files:
            self._add_path(jobId, file, True)

        i = 0
        while i < len(folders):
            if self.getCurThreads() < self.maxThreads:
                self._add_job(jobId)
                thread = threading.Thread(
                    target=self.scan_path,
                    args=(folders[i], nextLevel, jobId, True),
                    daemon=True,
                )
                thread.start()
            else:
                self.scan_path(folders[i], nextLevel, jobId)
            i += 1
        return

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
