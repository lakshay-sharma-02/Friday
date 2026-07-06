"""Shell command execution with killable processes."""

import subprocess
import time
import asyncio
import signal


# Global registry of running processes
_running_processes = {}


def run_shell(command: str, timeout: int = 30) -> dict:
    """Execute a shell command and return results.

    Args:
        command: Shell command to execute
        timeout: Maximum execution time in seconds

    Returns:
        Dict with output, exit_code, success, and optionally killed/reason fields
    """
    try:
        # Use Popen to get a live process handle
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Store process handle in global registry
        pid = process.pid
        _running_processes[pid] = {
            "process": process,
            "command": command,
            "started_at": time.time(),
        }

        try:
            # Wait for completion with timeout
            stdout, stderr = process.communicate(timeout=timeout)

            # Remove from registry
            _running_processes.pop(pid, None)

            output = stdout
            if stderr:
                output += "\n" + stderr

            return {
                "output": output.strip(),
                "exit_code": process.returncode,
                "success": process.returncode == 0,
                "pid": pid,
            }

        except subprocess.TimeoutExpired:
            # Try graceful termination first
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill if terminate didn't work
                process.kill()
                process.wait()

            # Remove from registry
            _running_processes.pop(pid, None)

            # Collect any output that was produced before timeout
            try:
                stdout, stderr = process.communicate(timeout=0.1)
                output = stdout
                if stderr:
                    output += "\n" + stderr
            except:
                output = ""

            return {
                "output": f"Command timed out after {timeout}s. Output before timeout:\n{output}".strip(),
                "exit_code": None,
                "success": False,
                "killed": True,
                "reason": "timeout exceeded",
                "pid": pid,
            }

    except Exception as e:
        return {
            "output": f"Error executing command: {str(e)}",
            "exit_code": 1,
            "success": False,
        }


def kill_process(pid: int) -> bool:
    """Kill a running process by PID.

    Args:
        pid: Process ID to kill

    Returns:
        True if process was killed, False if not found or already dead
    """
    proc_info = _running_processes.get(pid)
    if not proc_info:
        return False

    process = proc_info["process"]

    try:
        # Try graceful termination
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            # Force kill
            process.kill()
            process.wait()

        # Remove from registry
        _running_processes.pop(pid, None)
        return True

    except:
        return False


def get_running_processes() -> dict:
    """Get all currently running shell processes.

    Returns:
        Dict mapping PID to process info
    """
    # Clean up any processes that have finished
    finished = []
    for pid, info in _running_processes.items():
        if info["process"].poll() is not None:
            finished.append(pid)

    for pid in finished:
        _running_processes.pop(pid, None)

    return dict(_running_processes)
