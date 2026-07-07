"""Shell command execution tool.

Executes an arbitrary OS command without shell=True. Arguments are passed as
argv, so there is no shell interpretation of metacharacters. `run_shell` blocks
until the command finishes; `start_shell` launches it in the background so it
can be inspected/terminated via the `process` tool. Legacy `kill_process` /
`get_running_processes` helpers are retained for the pipeline watchdog.
"""

import os
import shlex
from tools.process_manager import (
    _run_process,
    spawn_process as _spawn_process,
    list_processes as _list_processes,
    terminate_process as _terminate_process,
)


def _to_argv(command):
    return shlex.split(command) if isinstance(command, str) else list(command)


def run_shell(command, *, cwd=None, timeout=30, env=None,
              cancel_event=None, graceful_timeout=5.0) -> dict:
    """Execute an OS command and return a structured result (blocks).

    Args:
        command: command string (shlex-split) or list of argv
        cwd: working directory
        timeout: max seconds before graceful kill
        env: extra/override environment variables (merged over os.environ)
        cancel_event: threading.Event that aborts early when set
    """
    argv = _to_argv(command)
    if not argv:
        return {
            "command": "",
            "argv": [],
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "success": False,
            "duration": 0.0,
            "pid": None,
            "killed": False,
            "reason": "empty command",
        }
    merged = {**os.environ, **env} if env else None
    return _run_process(argv, cwd=cwd, env=merged, timeout=timeout,
                         cancel_event=cancel_event, graceful_timeout=graceful_timeout)


def start_shell(command, *, cwd=None, env=None, graceful_timeout=5.0) -> dict:
    """Launch an OS command in the background; returns immediately with pid.

    The process is tracked until it exits and can be inspected or terminated
    via the `process` tool. Never blocks.
    """
    argv = _to_argv(command)
    if not argv:
        return {"command": "", "argv": [], "pid": None, "success": False,
                "reason": "empty command"}
    merged = {**os.environ, **env} if env else None
    return _spawn_process(argv, cwd=cwd, env=merged, graceful_timeout=graceful_timeout)


# --- Legacy API retained for core/pipeline.py watchdog compatibility ---

_running_processes = {}  # pid -> {"process", "command", "started_at"} (best-effort shim)


def kill_process(pid) -> bool:
    """Backwards-compatible kill. Delegates to the process manager."""
    res = _terminate_process(pid)
    _running_processes.pop(pid, None)
    return res.get("found", False)


def get_running_processes() -> dict:
    """Backwards-compatible listing. Returns pid -> info dict."""
    out = {}
    for entry in _list_processes():
        out[entry["pid"]] = {
            "process": None,
            "command": entry["command"],
            "started_at": entry["started_at"],
        }
        _running_processes.setdefault(entry["pid"], out[entry["pid"]])
    return out
