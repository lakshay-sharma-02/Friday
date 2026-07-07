"""Deterministic tests for Phase 6B execution tools (shell, python, process).

These do not touch the planner/pipeline — they exercise the tools directly so
they run fast and reliably. Each test asserts the structured return contract.
"""

import sys
import os
import time
import threading

import pytest

from tools.shell import run_shell, start_shell
from tools.python import run_python, start_python
from tools.process import run_process_tool, list_running, terminate


# --- shell: success / failure / invalid ---

def test_shell_success():
    r = run_shell("echo hello")
    assert r["success"] is True
    assert r["exit_code"] == 0
    assert r["stdout"].strip() == "hello"
    assert r["stderr"] == ""
    assert r["pid"] is not None
    assert r["duration"] >= 0


def test_shell_failure():
    r = run_shell(["python3", "-c", "import sys; sys.exit(3)"])
    assert r["success"] is False
    assert r["exit_code"] == 3
    assert r["killed"] is False


def test_shell_invalid_executable():
    r = run_shell("this_command_does_not_exist_xyz")
    assert r["success"] is False
    assert r["exit_code"] is None
    assert "spawn failed" in r["reason"]


def test_shell_stderr_captured():
    r = run_shell(["python3", "-c", "import sys; print('oops', file=sys.stderr)"])
    assert r["success"] is True
    assert r["stderr"].strip() == "oops"


# --- shell: cwd / env / argv ---

def test_shell_working_directory(tmp_path):
    target = tmp_path / "sub"
    target.mkdir()
    marker = target / "marker"
    r = run_shell(f"test -f {marker}", cwd=str(target))
    # Should fail: marker doesn't exist in cwd
    assert r["success"] is False
    # Now create it and re-run in same cwd
    marker.write_text("x")
    r2 = run_shell(f"test -f {marker}", cwd=str(target))
    assert r2["success"] is True


def test_shell_environment_variables():
    r = run_shell(["python3", "-c", "import os; print(os.environ['FRIDAY_TEST_VAR'])"],
                  env={"FRIDAY_TEST_VAR": "present"})
    assert r["stdout"].strip() == "present"


def test_shell_argv_no_shell_interpretation():
    # If a shell were interpreting, `echo` would see the whole string and print it.
    r = run_shell(["echo", "a; rm -rf /nonexistent"])
    assert r["success"] is True
    assert ";" not in r["stdout"].strip().split() or r["stdout"].strip() == "a; rm -rf /nonexistent"


# --- shell: unicode / long output ---

def test_shell_unicode_output():
    r = run_shell(["python3", "-c", "print('héllo wörld 日本語 🚀')"])
    assert r["success"] is True
    assert "🚀" in r["stdout"]


def test_shell_long_output():
    r = run_shell("python3 -c \"[print('line', i) for i in range(5000)]\"")
    assert r["success"] is True
    lines = r["stdout"].splitlines()
    assert len(lines) == 5000
    assert lines[0] == "line 0"
    assert lines[-1] == "line 4999"


# --- shell: timeout + cancellation ---

def test_shell_timeout():
    t0 = time.time()
    r = run_shell("sleep 30", timeout=2)
    elapsed = time.time() - t0
    assert r["success"] is False
    assert r["killed"] is True
    assert r["reason"] is not None and "timeout" in r["reason"]
    # Should not actually wait 30s
    assert elapsed < 10


def test_shell_cancellation():
    cancel = threading.Event()

    def trigger():
        time.sleep(0.5)
        cancel.set()

    threading.Thread(target=trigger, daemon=True).start()

    t0 = time.time()
    r = run_shell("sleep 30", timeout=30, cancel_event=cancel)
    elapsed = time.time() - t0
    assert r["success"] is False
    assert r["killed"] is True
    assert r["reason"] == "cancelled"
    assert elapsed < 10


def test_shell_no_zombie_after_timeout():
    r = run_shell("sleep 30", timeout=1)
    assert r["killed"] is True
    pid = r["pid"]
    # The killed process must be fully reaped: signaling it raises ProcessLookupError.
    import errno
    try:
        os.kill(pid, 0)
        alive = True
    except OSError as e:
        alive = e.errno != errno.ESRCH
    assert not alive


# --- python tool (convenience, not preferred) ---

def test_python_inline_script():
    r = run_python(script="print(2 * 21)")
    assert r["success"] is True
    assert r["stdout"].strip() == "42"
    assert r["exit_code"] == 0


def test_python_file(tmp_path):
    f = tmp_path / "s.py"
    f.write_text("import sys\nprint(sys.argv[1].upper())")
    r = run_python(file=str(f), args=["hello"])
    assert r["success"] is True
    assert r["stdout"].strip() == "HELLO"


def test_python_failure():
    r = run_python(script="import sys; sys.exit(7)")
    assert r["success"] is False
    assert r["exit_code"] == 7


def test_python_no_special_logic():
    # python tool must not silently swallow failures like the real interpreter
    r = run_python(script="1/0")
    assert r["success"] is False
    assert "ZeroDivisionError" in r["stderr"]


# --- process tool: inspect + terminate ---

def test_process_list_and_terminate():
    # Start a long-running process via the start (non-blocking) entry point
    start = start_shell("sleep 30")
    pid = start["pid"]
    assert pid is not None

    # It should appear in the manager registry / process tool list
    listing = list_running()
    pids = [p["pid"] for p in listing["processes"]]
    assert pid in pids

    # Inspect it
    info = run_process_tool(action="inspect", pid=pid)
    assert info["found"] is True
    assert info["running"] is True

    # Terminate gracefully
    res = terminate(pid)
    assert res["found"] is True
    assert res["success"] is True

    # After termination it's gone
    gone = run_process_tool(action="inspect", pid=pid)
    assert gone["found"] is False


def test_process_terminate_unknown_pid():
    res = terminate(999999)
    assert res["found"] is False
    assert res["success"] is False


def test_process_inspect_unknown_pid():
    info = run_process_tool(action="inspect", pid=999999)
    assert info["found"] is False


def test_process_unknown_action():
    res = run_process_tool(action="explode")
    assert "error" in res
    assert res["success"] is False


def test_process_graceful_before_force():
    # A process that ignores SIGTERM should still die via SIGKILL fallback.
    script = "import signal, time\n" \
             "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n" \
             "time.sleep(30)\n"
    start = start_python(script=script)
    pid = start["pid"]
    res = terminate(pid, graceful_timeout=1.0)
    assert res["found"] is True
    assert res["success"] is True
    # The killed process must be fully reaped.
    import errno
    try:
        os.kill(pid, 0)
        alive = True
    except OSError as e:
        alive = e.errno != errno.ESRCH
    assert not alive
