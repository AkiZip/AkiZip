# AkiZip Plugin Guide / AkiZip 插件开发规范

## 中文

### 1. 插件分两类

即时状态插件：
- 用来保存和读取应用当前状态。
- 不做耗时操作。
- 例如 `system.py` 保存当前选择的源文件、目标文件夹、文件信息状态。
- UI 可以直接调用这类对象的方法，因为它们应该很快返回。

耗时任务插件：
- 用来执行真正可能耗时的功能，例如压缩、解压、移动、复制、删除、大文件扫描。
- 必须通过 `JobQueue` 执行，不能直接在 UI 线程里运行。
- 例如 `sevenzip.py` 和 `system_job.py`。

### 2. 新增耗时功能的文件格式

新增一个插件文件，例如：

```python
def feature_name(arg1, arg2, timeout=-1, cancel_event=None):
    ...
    return "User readable result"


def register(commands):
    commands["group.feature"] = feature_name
```

要求：
- 函数名使用小写加下划线，例如 `move_path`。
- 命令名使用 `group.action` 格式，例如 `archive.extract`、`system.move`。
- `timeout=-1` 和 `cancel_event=None` 尽量保留，方便队列统一控制。
- 返回值应该是给日志显示的简短结果，不要返回复杂 UI 文本。
- 报错时直接抛出异常，例如 `FileNotFoundError`、`TimeoutError`、`RuntimeError`，由队列和 UI 统一显示。

### 3. 注册规范

每个耗时任务插件都提供 `register(commands)`。

然后在 `src/plugins/__init__.py` 里导入并注册：

```python
from . import sevenzip, system_job


def register_plugins(commands):
    sevenzip.register(commands)
    system_job.register(commands)
```

不要在 UI 里直接 import 具体插件函数。UI 应该通过：

```python
command = app.commands.get("group.feature")
app.job_queue.submit(command, args, timeout=60)
```

### 4. Queue / timeout / cancel 规范

耗时任务必须支持队列：
- UI 点击按钮后只提交任务。
- `JobQueue` 会把状态从 `pending` 改成 `working`，完成后改成 `finished/error/timeout/cancelled`。
- UI 根据状态更新右侧日志。

如果功能能被取消：
- 定期检查 `cancel_event.is_set()`。
- 如果已取消，抛出 `RuntimeError("Cancelled")`。

如果功能能超时：
- 定期检查执行时间。
- 超时后抛出 `TimeoutError(...)`。

如果调用外部进程：
- 参考 `sevenzip.py`。
- 用 `subprocess.Popen`。
- 取消或超时时杀掉进程。

如果是文件系统操作：
- 参考 `system_job.py`。
- 大文件复制/移动要分块处理，并在每个循环检查取消和超时。

### 5. UI 规范

UI 只负责：
- 读取用户输入。
- 校验是否选择了必要路径。
- 调用 `_run_command("group.feature", *args)`。
- 显示日志和状态。

UI 不应该：
- 直接写压缩、解压、移动等实际逻辑。
- 直接运行耗时函数。
- 直接阻塞主线程。

### 6. 命名建议

常用命令分组：
- `archive.*`：压缩包相关，例如 `archive.info`、`archive.compress`、`archive.extract`。
- `system.*`：文件系统相关，例如 `system.move`。
- `file.*`：单文件操作。
- `folder.*`：文件夹操作。

日志显示可以在 `window.py` 的 `_command_summary()` 和 `_command_preview()` 里补充，让用户看到简单文字，例如：
- `Compress test.zip`
- `Extract test.zip`
- `Move file.txt`

---

## English

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
