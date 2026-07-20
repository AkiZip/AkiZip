# status.py
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
import time
from enum import Enum


class _status(str, Enum):
    PENDING = "pending"
    WORKING = "working"
    FINISHED = "finished"
    WARNING = "warning"
    TIMEOUT = "timeout"
    ERROR = "error"
    CANCELLED = "cancelled"


class status:
    def __init__(self, task_id, msg="", timeout=-1):
        self.task_id = task_id
        self.msg = msg
        self.timeout = timeout
        self.status = _status.PENDING
        self.success = False
        self.created_at = time.time()
        self.started_at = None
        self.finished_at = None
        self.progress = None
        self.eta = None
        self._on_progress = None

    def start(self, msg=None):
        if msg is not None:
            self.msg = msg
        self.status = _status.WORKING
        self.success = False
        self.started_at = time.time()
        self.finished_at = None
        return self

    def set_on_progress(self, callback):
        self._on_progress = callback
        return self

    def set_progress(self, percent):
        self.progress = percent
        if self.started_at is not None and percent is not None and percent > 0:
            elapsed = time.time() - self.started_at
            self.eta = max(0, elapsed * (100.0 / percent) - elapsed)
        else:
            self.eta = None
        if self._on_progress is not None:
            self._on_progress(percent)
        return self

    def failed(self, msg=None):
        if msg is not None:
            self.msg = msg
        self.status = _status.ERROR
        self.success = False
        self.finished_at = time.time()
        return self

    def finished(self, msg=None):
        if msg is not None:
            self.msg = msg
        self.status = _status.FINISHED
        self.success = True
        self.finished_at = time.time()
        return self

    def warning(self, msg=None):
        if msg is not None:
            self.msg = msg
        self.status = _status.WARNING
        self.success = True
        self.finished_at = time.time()
        return self


    def timed_out(self, msg=None):
        if msg is not None:
            self.msg = msg
        self.status = _status.TIMEOUT
        self.success = False
        self.finished_at = time.time()
        return self

    def cancelled(self, msg=None):
        if msg is not None:
            self.msg = msg
        self.status = _status.CANCELLED
        self.success = False
        self.finished_at = time.time()
        return self

    def is_timeout(self):
        if self.timeout < 0 or self.started_at is None:
            return False
        return self.status == _status.WORKING and time.time() - self.started_at >= self.timeout

    def check_timeout(self, msg=None):
        if self.is_timeout():
            self.timed_out(msg)
            return True
        return False

    def is_done(self):
        return self.status in (
            _status.FINISHED,
            _status.WARNING,
            _status.TIMEOUT,
            _status.ERROR,
            _status.CANCELLED,
        )

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "success": self.success,
            "msg": self.msg,
            "timeout": self.timeout,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    def __str__(self):
        return f"{self.task_id}: {self.status.value} - {self.msg}"

