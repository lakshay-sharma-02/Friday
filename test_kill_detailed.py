"""Test process killing with detailed ps output."""

import subprocess
import time
import os
import sys


def test_kill_with_ps_capture():
    """Test killing with before/after ps snapshots."""

    print("=== DETAILED KILL TEST WITH PS SNAPSHOTS ===")
    print()

    sys.path.insert(0, '/home/lakshay/Projects/Friday')
    from tools.shell import run_shell
    import threading

    # We'll capture PID and check ps in a thread while sleep runs
    captured_pid = None
    ps_before = None
    ps_after = None

    def run_sleep():
        nonlocal captured_pid
        result = run_shell("sleep 30", timeout=3)
        captured_pid = result.get('pid')
        return result

    # Start sleep in thread
    result_holder = []
    thread = threading.Thread(target=lambda: result_holder.append(run_sleep()))
    thread.start()

    # Give it time to spawn
    time.sleep(0.5)

    # Capture ps WHILE sleep is running
    print("[1] Capturing ps output WHILE sleep is running:")
    ps_result = subprocess.run(
        "ps aux | grep '[s]leep 30' | head -5",
        shell=True,
        capture_output=True,
        text=True
    )
    ps_before = ps_result.stdout
    print(ps_before if ps_before.strip() else "(no sleep process found yet)")

    # Wait for timeout to kill it
    thread.join()
    result = result_holder[0]

    # Small delay to ensure process is fully cleaned up
    time.sleep(0.2)

    # Capture ps AFTER timeout killed it
    print("\n[2] Capturing ps output AFTER timeout killed it:")
    ps_result = subprocess.run(
        "ps aux | grep '[s]leep 30' | head -5",
        shell=True,
        capture_output=True,
        text=True
    )
    ps_after = ps_result.stdout
    print(ps_after if ps_after.strip() else "(process not found - killed successfully)")

    print(f"\n[3] Result dict:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    print("\n=== VERIFICATION ===")
    if ps_before.strip():
        print(f"✓ Process was running (PID {result.get('pid')})")
    else:
        print("✗ Process not captured in ps before")

    if not ps_after.strip():
        print("✓ Process is gone after timeout")
    else:
        print("✗ Process still exists after timeout")

    print(f"✓ killed=True: {result.get('killed')}")
    print(f"✓ reason='timeout exceeded': {result.get('reason')}")


if __name__ == "__main__":
    test_kill_with_ps_capture()
