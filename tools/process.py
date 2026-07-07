"""Process inspection and control tool.

Lets Friday list, inspect, and terminate processes it previously started via
the execution tools. Termination is always graceful-first (SIGTERM, then
SIGKILL) so no zombies are left behind.
"""

from tools.process_manager import (
    list_processes as _list_processes,
    inspect_process as _inspect_process,
    terminate_process as _terminate_process,
)


def list_running() -> dict:
    """List processes Friday currently has running."""
    procs = _list_processes()
    return {"processes": procs, "count": len(procs), "success": True,
            "output": f"{len(procs)} process(es) running"}


def inspect(pid) -> dict:
    """Inspect a single managed process; returns dict with found flag."""
    info = _inspect_process(pid)
    if info is None:
        return {"pid": pid, "found": False, "success": False,
                "output": "process not found or already finished"}
    return {"pid": pid, "found": True, "success": True, **info,
            "output": f"pid {pid} running: {' '.join(info['command'])}"}


def terminate(pid, graceful_timeout=5.0) -> dict:
    """Gracefully terminate a managed process."""
    res = _terminate_process(pid, graceful_timeout=graceful_timeout)
    res["output"] = res.get("reason") or (f"terminated pid {pid}" if res.get("success") else "terminate failed")
    return res


def run_process_tool(*, action="list", pid=None, graceful_timeout=5.0) -> dict:
    """Single entry point for the `process` tool.

    Args:
        action: one of "list" | "inspect" | "terminate"
        pid: target pid for inspect/terminate
    """
    action = (action or "list").lower()
    if action == "list":
        return list_running()
    if action == "inspect":
        if pid is None:
            return {"error": "pid required for inspect", "success": False,
                    "output": "pid required"}
        return inspect(pid)
    if action == "terminate":
        if pid is None:
            return {"error": "pid required for terminate", "success": False,
                    "output": "pid required"}
        return terminate(pid, graceful_timeout=graceful_timeout)
    return {"error": f"unknown action '{action}'", "success": False,
            "output": f"unknown action '{action}'"}
