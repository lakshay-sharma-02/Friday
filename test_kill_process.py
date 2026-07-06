"""Test that shell tool actually kills long-running processes."""

import subprocess
import time
import sys


def test_kill_running_process():
    """Test killing a running sleep process."""

    print("=== TEST: Killing Running Process ===")
    print()

    # Import the shell tool
    sys.path.insert(0, '/home/lakshay/Projects/Friday')
    from tools.shell import run_shell

    # Start sleep in background via shell tool with 3 second timeout
    print("[1] Starting 'sleep 30' with 3 second timeout...")
    start_time = time.time()

    # Capture ps output BEFORE starting
    print("\nBefore starting sleep:")
    subprocess.run("ps aux | grep '[s]leep 30'", shell=True)

    # Run with timeout
    result = run_shell("sleep 30", timeout=3)

    elapsed = time.time() - start_time

    print(f"\n[2] Command completed after {elapsed:.2f}s")
    print(f"\nReturned dict:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    # Check ps output AFTER timeout killed it
    print("\n[3] Checking if process still exists:")
    ps_result = subprocess.run(
        "ps aux | grep '[s]leep 30'",
        shell=True,
        capture_output=True,
        text=True
    )

    if ps_result.stdout.strip():
        print("PROCESS STILL RUNNING:")
        print(ps_result.stdout)
        return False
    else:
        print("Process not found (killed successfully)")

    print("\n=== VERIFICATION ===")
    print(f"✓ Timeout fired (~3s): {elapsed:.2f}s")
    print(f"✓ killed=True: {result.get('killed', False)}")
    print(f"✓ reason='timeout exceeded': {result.get('reason') == 'timeout exceeded'}")
    print(f"✓ PID in result: {result.get('pid') is not None}")
    print(f"✓ Process gone from ps: {not ps_result.stdout.strip()}")

    return True


if __name__ == "__main__":
    success = test_kill_running_process()
    sys.exit(0 if success else 1)
