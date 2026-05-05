# AkiZip Plugin Guide 

### 1. Two plugin types

Immediate state plugins:
- Store and read current application state.
- Must not run slow operations.
- Example: `system.py` stores the selected source path, destination folder, and file information state.
- The UI may call these methods directly because they should return quickly.

Long-running job plugins:
- Run operations that may take time, such as compress, extract, move, copy, delete, or large file scanning.
- Must run through `JobQueue`, not directly on the UI thread.
- Examples: `sevenzip.py` and `system_job.py`.

### 2. Long-running feature file format

Add a plugin file, for example:

```python
def feature_name(arg1, arg2, timeout=-1, cancel_event=None):
    ...
    return "User readable result"


def register(commands):
    commands["group.feature"] = feature_name
```

Rules:
- Use lowercase function names with underscores, for example `move_path`.
- Use `group.action` command names, for example `archive.extract` or `system.move`.
- Keep `timeout=-1` and `cancel_event=None` when possible, so the queue can control the job.
- Return a short result string for the log. Do not return UI-specific content.
- Raise normal exceptions on failure, such as `FileNotFoundError`, `TimeoutError`, or `RuntimeError`. The queue and UI will display them.

### 3. Registration rules

Every long-running job plugin should expose `register(commands)`.

Then import and register it in `src/plugins/__init__.py`:

```python
from . import sevenzip, system_job


def register_plugins(commands):
    sevenzip.register(commands)
    system_job.register(commands)
```

Do not import concrete plugin functions directly in the UI. The UI should use:

```python
command = app.commands.get("group.feature")
app.job_queue.submit(command, args, timeout=60)
```

### 4. Queue / timeout / cancel rules

Long-running jobs must support the queue:
- A UI button should only submit the job.
- `JobQueue` changes the task from `pending` to `working`, then to `finished/error/timeout/cancelled`.
- The UI updates the right-side log from those states.

If a feature can be cancelled:
- Check `cancel_event.is_set()` regularly.
- Raise `RuntimeError("Cancelled")` when cancellation is requested.

If a feature can time out:
- Check elapsed time regularly.
- Raise `TimeoutError(...)` when time runs out.

If the feature calls an external process:
- Follow `sevenzip.py`.
- Use `subprocess.Popen`.
- Kill the process on cancel or timeout.

If the feature performs filesystem work:
- Follow `system_job.py`.
- Copy or move large files in chunks, and check cancel/timeout inside the loop.

### 5. UI rules

The UI should only:
- Read user input.
- Check required paths.
- Call `_run_command("group.feature", *args)`.
- Show logs and status.

The UI should not:
- Implement compress, extract, move, or other real job logic.
- Run slow functions directly.
- Block the main thread.

### 6. Naming suggestions

Common command groups:
- `archive.*`: archive operations, such as `archive.info`, `archive.compress`, `archive.extract`.
- `system.*`: filesystem operations, such as `system.move`.
- `file.*`: single file operations.
- `folder.*`: folder operations.

Add user-facing summaries in `_command_summary()` and `_command_preview()` in `window.py`, so the log stays simple, for example:
- `Compress test.zip`
- `Extract test.zip`
- `Move file.txt`
