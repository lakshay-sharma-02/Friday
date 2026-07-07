"""Python execution tool.

Convenience wrapper that runs Python through the system interpreter. This is
NOT the preferred execution path and carries no special capabilities — it just
delegates to the OS interpreter exactly as `shell` would for any language.
"""

import sys
import shlex
from tools.process_manager import _run_process, spawn_process as _spawn_process


def run_python(*, script=None, file=None, args=None, cwd=None, timeout=30,
               env=None, cancel_event=None) -> dict:
    """Execute Python via the configured interpreter.

    Args:
        script: inline Python source to run (mutually exclusive with file)
        file: path to a .py file to execute
        args: list/tuple of argv passed to the script
        cwd: working directory
        timeout: max seconds
        env: extra/override environment variables
        cancel_event: threading.Event to abort early
    """
    interpreter = sys.executable or "python3"
    argv = [interpreter]
    if script is not None:
        argv += ["-c", script]
    elif file is not None:
        argv += [file]
    else:
        return {
            "command": " ".join(argv),
            "argv": argv,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "success": False,
            "duration": 0.0,
            "pid": None,
            "killed": False,
            "reason": "specify script or file",
        }
    if args:
        argv += list(args)

    merged = None
    if env:
        merged = {**sys.modules["os"].environ, **env}

    result = _run_process(argv, cwd=cwd, env=merged, timeout=timeout,
                          cancel_event=cancel_event)
    return result


def start_python(*, script=None, file=None, args=None, cwd=None, env=None,
                 graceful_timeout=5.0) -> dict:
    """Launch Python in the background; returns immediately with pid."""
    interpreter = sys.executable or "python3"
    argv = [interpreter]
    if script is not None:
        argv += ["-c", script]
    elif file is not None:
        argv += [file]
    else:
        return {"command": " ".join(argv), "argv": argv, "pid": None,
                "success": False, "reason": "specify script or file"}
    if args:
        argv += list(args)
    merged = None
    if env:
        merged = {**sys.modules["os"].environ, **env}
    return _spawn_process(argv, cwd=cwd, env=merged, graceful_timeout=graceful_timeout)
