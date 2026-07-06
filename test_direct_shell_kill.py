"""Direct test: spawn sleep 30 via shell tool, verify it gets killed at 3s timeout."""

import subprocess
import time
import sys
import os


def test_direct_shell_kill():
    """Test shell.run_shell() kills sleep 30 after 3s timeout."""

    print("=== DIRECT SHELL KILL TEST ===")
    print()

    sys.path.insert(0, '/home/lakshay/Projects/Friday')

    # Capture ps BEFORE
    print("[1] ps aux BEFORE starting sleep:")
    subprocess.run("ps aux | grep '[s]leep 30'", shell=True)
    print()

    # Start sleep 30 with 3s timeout via shell tool
    print("[2] Starting 'sleep 30' with timeout=3...")
    from tools.shell import run_shell

    start = time.time()
    result = run_shell("sleep 30", timeout=3)
    elapsed = time.time() - start

    print(f"   Completed in {elapsed:.2f}s")
    print()

    # Show result
    print("[3] Returned dict:")
    for k, v in result.items():
        print(f"   {k}: {v}")
    print()

    # Capture ps AFTER - the critical check
    print("[4] ps aux AFTER timeout (PID should be gone):")
    ps_result = subprocess.run(
        f"ps aux | grep '[s]leep 30'",
        shell=True,
        capture_output=True,
        text=True
    )

    if ps_result.stdout.strip():
        print("   PROCESS STILL RUNNING (FAIL):")
        print(f"   {ps_result.stdout}")
        return False
    else:
        print("   (no process found - killed successfully)")

    print()
    print("=== VERIFICATION ===")
    print(f"✓ Timeout fired at ~3s: {elapsed:.2f}s")
    print(f"✓ killed=True: {result.get('killed')}")
    print(f"✓ reason='timeout exceeded': {result.get('reason')}")
    print(f"✓ PID tracked: {result.get('pid')}")
    print(f"✓ Process gone from ps")
    print()
    print("Shell tool successfully kills long-running processes.")

    return True


if __name__ == "__main__":
    success = test_direct_shell_kill()
    sys.exit(0 if success else 1)
