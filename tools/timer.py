"""Timer tool - named countdowns with pause/resume/cancel.

In-memory, process-local. Timers are not persisted across restarts.
"""

import time
import threading
from typing import Optional, Callable, Dict

_timers: Dict[str, dict] = {}
_lock = threading.Lock()


class TimerError(Exception):
    pass


def _fire(name: str) -> None:
    with _lock:
        entry = _timers.get(name)
        if not entry or entry.get("fired"):
            return
        entry["fired"] = True
        cb = entry.get("callback")
        _timers.pop(name, None)
    if cb:
        cb()


def _create(name: str, seconds: float, callback: Optional[Callable] = None) -> None:
    if name in _timers:
        raise TimerError(f"Timer '{name}' already exists")
    _timers[name] = {
        "start": time.monotonic(),
        "duration": seconds,
        "remaining": seconds,
        "paused": False,
        "fired": False,
        "callback": callback,
    }
    if callback:
        threading.Timer(seconds, lambda: _fire(name)).start()


def _remaining(name: str) -> float:
    entry = _timers.get(name)
    if not entry:
        raise TimerError(f"Unknown timer '{name}'")
    if entry["paused"]:
        return entry["remaining"]
    elapsed = time.monotonic() - entry["start"]
    return max(0.0, entry["duration"] - elapsed)


def _pause(name: str) -> float:
    entry = _timers.get(name)
    if not entry:
        raise TimerError(f"Unknown timer '{name}'")
    if entry["paused"]:
        return entry["remaining"]
    entry["remaining"] = _remaining(name)
    entry["paused"] = True
    return entry["remaining"]


def _resume(name: str) -> float:
    entry = _timers.get(name)
    if not entry:
        raise TimerError(f"Unknown timer '{name}'")
    if not entry["paused"]:
        return _remaining(name)
    entry["start"] = time.monotonic()
    entry["duration"] = entry["remaining"]
    entry["paused"] = False
    return entry["remaining"]


def _cancel(name: str) -> bool:
    return _timers.pop(name, None) is not None


def _list() -> dict:
    return {
        name: {"remaining": _remaining(name), "paused": v["paused"]}
        for name, v in _timers.items()
    }


def run_timer(
    *,
    action: str,
    name: Optional[str] = None,
    seconds: Optional[float] = None,
) -> dict:
    """Single entry point for the `timer` tool.

    action: create | remaining | pause | resume | cancel | list
    name:   timer identifier (required for all but list)
    seconds: duration for create
    """
    action = (action or "").lower()
    try:
        if action == "create":
            if not name:
                return {"error": "name required", "success": False, "output": "name required"}
            if seconds is None:
                return {"error": "seconds required", "success": False, "output": "seconds required"}
            with _lock:
                _create(name, float(seconds))
            return {"name": name, "seconds": seconds, "success": True,
                    "output": f"timer '{name}' created for {seconds}s"}
        if action == "remaining":
            if not name:
                return {"error": "name required", "success": False, "output": "name required"}
            rem = _remaining(name)
            return {"name": name, "remaining": rem, "success": True,
                    "output": f"timer '{name}' has {rem:.3f}s remaining"}
        if action == "pause":
            if not name:
                return {"error": "name required", "success": False, "output": "name required"}
            rem = _pause(name)
            return {"name": name, "remaining": rem, "success": True,
                    "output": f"timer '{name}' paused at {rem:.3f}s"}
        if action == "resume":
            if not name:
                return {"error": "name required", "success": False, "output": "name required"}
            rem = _resume(name)
            return {"name": name, "remaining": rem, "success": True,
                    "output": f"timer '{name}' resumed, {rem:.3f}s left"}
        if action == "cancel":
            if not name:
                return {"error": "name required", "success": False, "output": "name required"}
            ok = _cancel(name)
            return {"name": name, "success": ok,
                    "output": f"timer '{name}' {'cancelled' if ok else 'not found'}"}
        if action == "list":
            timers = _list()
            return {"timers": timers, "count": len(timers), "success": True,
                    "output": f"{len(timers)} active timer(s)"}
        return {"error": f"unknown action '{action}'", "success": False,
                "output": f"unknown action '{action}'"}
    except TimerError as e:
        return {"error": str(e), "success": False, "output": str(e)}
    except Exception as e:  # pragma: no cover
        return {"error": repr(e), "success": False, "output": repr(e)}
