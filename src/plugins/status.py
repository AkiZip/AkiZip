import time
from enum import Enum

UNKNOWN_TIME_ESTIMATE = ("--", "--", "--")

class _status(str, Enum):
    PENDING = "pending"
    WORKING = "working"
    FINISHED = "finished"
    WARNING = "warning"
    TIMEOUT = "timeout"
    ERROR = "error"
    CANCELLED = "cancelled"

class timer():
    def __init__(self):
        self.starttime = time.time()
        self.lastPercentage = -1
        self.lastSecond = -1
        self.lastSpeed = None

    def now(self):
        return time.time()

    def get_time(self):
        return self.now() - self.starttime

    def estimate_time(self,percentage):#-> timeTake, averageTimeLeft, curSpeedTimeLeft
        try:
            percentage = float(percentage)
        except (TypeError, ValueError):
            return UNKNOWN_TIME_ESTIMATE

        if not 0 < percentage < 100:
            return UNKNOWN_TIME_ESTIMATE

        now = self.now()
        timeTake = now - self.starttime
        if timeTake <= 0:
            return UNKNOWN_TIME_ESTIMATE

        aveSpeed = percentage / timeTake
        curSpeed = self.lastSpeed if self.lastSpeed is not None else aveSpeed

        if self.lastSecond == -1 or self.lastPercentage == -1:
            self.lastPercentage = percentage
            self.lastSecond = now
        elif now - self.lastSecond >= 1:
            percentageChange = percentage - self.lastPercentage
            secondChange = now - self.lastSecond
            if percentageChange > 0 and secondChange > 0:
                curSpeed = percentageChange / secondChange
                self.lastSpeed = curSpeed
            self.lastSecond = now
            self.lastPercentage = percentage

        if aveSpeed <= 0 or curSpeed <= 0:
            return UNKNOWN_TIME_ESTIMATE

        averageTimeLeft = (100 - percentage) / aveSpeed
        curSpeedTimeLeft = (100 - percentage) / curSpeed
        return self.format(timeTake), self.format(averageTimeLeft), self.format(curSpeedTimeLeft)

    def format(self,second):
        if not isinstance(second, (int, float)):
            return "--"
        if second < 0:
            return "--"

        second = int(second)
        days = second // 86400
        second %= 86400
        hours = second // 3600
        second %= 3600
        minutes = second // 60
        seconds = second % 60

        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


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
        self.progress_timer = timer()
        self.progress_times = UNKNOWN_TIME_ESTIMATE
        self._on_progress = None

    def start(self, msg=None):
        if msg is not None:
            self.msg = msg
        self.status = _status.WORKING
        self.success = False
        self.started_at = time.time()
        self.finished_at = None
        self.progress = None
        self.progress_timer = timer()
        self.progress_times = UNKNOWN_TIME_ESTIMATE
        return self

    def set_on_progress(self, callback):
        self._on_progress = callback
        return self

    def set_progress(self, percent):
        self.progress = percent
        try:
            numeric_percent = float(percent)
        except (TypeError, ValueError):
            numeric_percent = None
        if numeric_percent is not None and numeric_percent >= 100:
            elapsed = self.progress_timer.format(self.progress_timer.get_time())
            self.progress_times = (elapsed, "0s", "0s")
        else:
            self.progress_times = self.progress_timer.estimate_time(percent)
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
            "progress": self.progress,
            "progress_times": self.progress_times,
        }

    def __str__(self):
        return f"{self.task_id}: {self.status.value} - {self.msg}"
