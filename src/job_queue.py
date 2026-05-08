import inspect
import queue
import threading
import time

from .plugins.status import status as TaskStatus


class JobHandle:
    def __init__(self, task_status):
        self.status = task_status
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()
        return self.status


class JobQueue:
    def __init__(self, scheduler=None, default_timeout=-1):
        self._queue = queue.Queue()
        self._scheduler = scheduler or self._schedule_on_main_thread
        self._default_timeout = default_timeout
        self._stopped = False
        self._thread = threading.Thread(target=self._run, name='AkizipJobQueue')

    @property
    def default_timeout(self):
        return self._default_timeout

    @default_timeout.setter
    def default_timeout(self, value):
        self._default_timeout = value

    def start(self):
        self._thread.start()

    def stop(self):
        self._stopped = True
        self._queue.put(None)
        self._thread.join()

    def submit(
        self,
        function,
        args=(),
        on_success=None,
        on_error=None,
        task_status=None,
        timeout=None,
        task_id=None,
        msg=None,
        on_status=None,
    ):
        if task_status is None:
            task_status = TaskStatus(
                task_id or getattr(function, "__name__", "job"),
                msg or "",
                timeout if timeout is not None else self._default_timeout,
            )
        elif timeout is not None:
            task_status.timeout = timeout

        handle = JobHandle(task_status)

        self._queue.put((
            function,
            args,
            on_success,
            on_error,
            task_status,
            on_status,
            handle,
        ))
        return handle

    def _schedule_on_main_thread(self, callback, *args):
        from gi.repository import GLib

        GLib.idle_add(callback, *args)

    def _run(self):
        while not self._stopped:
            job = self._queue.get()
            if job is None:
                break

            function, args, on_success, on_error, task_status, on_status, handle = job
            if handle.cancel_event.is_set():
                task_status.cancelled("Cancelled")
                self._notify_status(on_status, task_status)
                self._queue.task_done()
                continue

            task_status.start(task_status.msg)
            if on_status is not None:
                task_status.set_on_progress(lambda _p: self._notify_status(on_status, task_status))
            self._notify_status(on_status, task_status)
            started_at = time.time()

            try:
                result = self._call_function(function, args, task_status, handle)
            except Exception as error:
                if handle.cancel_event.is_set():
                    task_status.cancelled(str(error) or "Cancelled")
                elif isinstance(error, TimeoutError):
                    task_status.timed_out(str(error))
                else:
                    task_status.failed(str(error))
                self._notify_status(on_status, task_status)
                if on_error is not None:
                    self._scheduler(on_error, error)
            else:
                elapsed = time.time() - started_at
                if task_status.timeout >= 0 and elapsed >= task_status.timeout:
                    error = TimeoutError(f"Job timed out after {task_status.timeout} seconds")
                    task_status.timed_out(str(error))
                    self._notify_status(on_status, task_status)
                    if on_error is not None:
                        self._scheduler(on_error, error)
                else:
                    task_status.finished(task_status.msg)
                    self._notify_status(on_status, task_status)
                    if on_success is not None:
                        self._scheduler(on_success, result)
            finally:
                self._queue.task_done()

    def _call_function(self, function, args, task_status, handle):
        signature = inspect.signature(function)
        parameters = signature.parameters
        accepts_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )
        kwargs = {}

        if accepts_kwargs or "timeout" in parameters:
            kwargs["timeout"] = task_status.timeout
        if accepts_kwargs or "cancel_event" in parameters:
            kwargs["cancel_event"] = handle.cancel_event
        if accepts_kwargs or "task_status" in parameters:
            kwargs["task_status"] = task_status

        return function(*args, **kwargs)

    def _notify_status(self, on_status, task_status):
        if on_status is not None:
            self._scheduler(on_status, task_status)
