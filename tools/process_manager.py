"""Shared process execution and tracking for Friday execution tools.

Single source of truth for spawning OS processes safely: no shell=True,
process-group kill (no orphaned/zombie children), enforced timeouts, and a
global registry of processes Friday has started so they can be inspected or
terminated later.
"""

import os
import signal
import shlex
import time
import threading
import subprocess
from dataclasses import dataclass, field
from typing import Optional

# pid -> ManagedProcess for every process Friday has started and not reaped.
_PROCESSES: dict[int, "ManagedProcess"] = {}
_LOCK = threading.Lock()

GRACEFUL_TIMEOUT = 5.0


@dataclass
class ManagedProcess:
    proc: subprocess.Popen
    argv: list[str]
    started_at: float
    cwd: Optional[str] = None
    cancel_event: Optional[threading.Event] = None
    exit_code: Optional[int] = None
    killed: bool = False
    reason: Optional[str] = None
    graceful_timeout: float = GRACEFUL_TIMEOUT

    @property
    def pid(self) -> int:
        return self.proc.pid


def _split_command(command) -> list[str]:
    """Normalize a command into argv. Accepts a string (shlex) or list."""
    if isinstance(command, (list, tuple)):
        return list(command)
    return shlex.split(command)


def _kill_group(proc: subprocess.Popen, graceful_timeout: float = GRACEFUL_TIMEOUT) -> None:
    """Terminate a process and its whole group, SIGTERM then SIGKILL."""
    pgid = None
    try:
        pgid = os.getpgid(proc.pid)
    except (ProcessLookupError, OSError):
        pass

    if pgid is not None:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
    else:
        try:
            proc.terminate()
        except (ProcessLookupError, OSError):
            pass

    try:
        proc.wait(timeout=graceful_timeout)
        return
    except subprocess.TimeoutExpired:
        pass

    if pgid is not None:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
    else:
        try:
            proc.kill()
        except (ProcessLookupError, OSError):
            pass
    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        pass


def _run_process(argv, *, cwd=None, env=None, timeout=None,
                 cancel_event=None, graceful_timeout=GRACEFUL_TIMEOUT) -> dict:
    """Spawn and wait on an OS process. Never blocks past `timeout` forever.

    Returns a structured result dict consumed by the execution tools.
    """
    t0 = time.perf_counter()
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            start_new_session=True,
        )
    except (FileNotFoundError, PermissionError, OSError) as e:
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
            "reason": f"spawn failed: {e}",
        }

    managed = ManagedProcess(proc=proc, argv=argv, started_at=t0, cwd=cwd,
                             cancel_event=cancel_event)
    with _LOCK:
        _PROCESSES[proc.pid] = managed

    timed_out = False
    cancelled = False
    pump = threading.Thread(target=proc.wait, daemon=True)
    pump.start()

    interval = 0.05
    while pump.is_alive():
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            break
        if timeout is not None and (time.perf_counter() - t0) >= timeout:
            timed_out = True
            break
        time.sleep(interval)

    duration = time.perf_counter() - t0

    if pump.is_alive():
        _kill_group(proc, graceful_timeout)
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            pass

    stdout, stderr = "", ""
    try:
        out, err = proc.communicate(timeout=0.5)
        stdout, stderr = out or "", err or ""
    except Exception:
        pass

    with _LOCK:
        _PROCESSES.pop(proc.pid, None)

    managed.exit_code = proc.returncode
    managed.killed = timed_out or cancelled

    result = {
        "command": " ".join(argv),
        "argv": argv,
        "exit_code": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "output": stdout + ("\n" + stderr if stderr else ""),
        "success": proc.returncode == 0 and not timed_out and not cancelled,
        "duration": round(duration, 4),
        "pid": proc.pid,
        "killed": managed.killed,
        "reason": None,
    }
    if timed_out:
        result["reason"] = f"timeout exceeded ({timeout}s)"
    elif cancelled:
        result["reason"] = "cancelled"
    return result


def spawn_process(argv, *, cwd=None, env=None, graceful_timeout=GRACEFUL_TIMEOUT) -> dict:
    """Start a process and return immediately, tracked until it exits.

    Unlike _run_process this does not block; the process runs in the
    background and is automatically reaped (removed from the registry) when it
    finishes, so it can be inspected or terminated via the process tool.
    """
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            start_new_session=True,
        )
    except (FileNotFoundError, PermissionError, OSError) as e:
        return {
            "command": " ".join(argv),
            "argv": argv,
            "pid": None,
            "success": False,
            "reason": f"spawn failed: {e}",
        }

    with _LOCK:
        _PROCESSES[proc.pid] = ManagedProcess(
            proc=proc, argv=argv, started_at=time.perf_counter(),
            cwd=cwd, graceful_timeout=graceful_timeout,
        )

    def _reap():
        try:
            proc.wait()
        finally:
            with _LOCK:
                _PROCESSES.pop(proc.pid, None)

    threading.Thread(target=_reap, daemon=True).start()

    return {
        "command": " ".join(argv),
        "argv": argv,
        "pid": proc.pid,
        "success": True,
    }


def list_processes() -> list[dict]:
    """Snapshot of processes Friday currently has running."""
    with _LOCK:
        live = {}
        for pid, mp in list(_PROCESSES.items()):
            if mp.proc.poll() is None:
                live[pid] = mp
            else:
                _PROCESSES.pop(pid, None)
    return [
        {
            "pid": mp.pid,
            "command": " ".join(mp.argv),
            "cwd": mp.cwd,
            "started_at": mp.started_at,
            "running": True,
        }
        for mp in live.values()
    ]


def inspect_process(pid: int) -> Optional[dict]:
    """Detailed view of one managed process, or None if unknown/finished."""
    with _LOCK:
        mp = _PROCESSES.get(pid)
        if mp is None:
            return None
        finished = mp.proc.poll() is not None
        if finished:
            _PROCESSES.pop(pid, None)
            return None
    return {
        "pid": mp.pid,
        "command": " ".join(mp.argv),
        "cwd": mp.cwd,
        "started_at": mp.started_at,
        "running": True,
    }


def terminate_process(pid: int, graceful_timeout: float = GRACEFUL_TIMEOUT) -> dict:
    """Gracefully terminate a managed process (SIGTERM then SIGKILL).

    Returns structured result; `found` is False when pid is unknown/unreapable.
    """
    with _LOCK:
        mp = _PROCESSES.get(pid)
        if mp is None:
            return {"pid": pid, "found": False, "success": False,
                    "reason": "unknown or already finished"}
        argv = list(mp.argv)
        cancel_event = mp.cancel_event
        g_timeout = mp.graceful_timeout

    if cancel_event is not None:
        cancel_event.set()

    _kill_group(mp.proc, g_timeout)
    try:
        mp.proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        pass

    with _LOCK:
        _PROCESSES.pop(pid, None)

    return {
        "pid": pid,
        "command": " ".join(argv),
        "found": True,
        "success": True,
        "exit_code": mp.proc.returncode,
        "reason": "terminated",
    }
