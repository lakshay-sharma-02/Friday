"""Git operations."""

import subprocess


def git_status() -> dict:
    """Check git repository status.

    Returns:
        Dict with output and success fields
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 128:
            return {
                "output": "Not a git repository",
                "exit_code": 128,
                "success": False,
            }

        output = result.stdout.strip()
        if not output:
            status_msg = "No uncommitted changes"
        else:
            lines = output.split("\n")
            status_msg = f"Found {len(lines)} uncommitted change(s):\n{output}"

        return {
            "output": status_msg,
            "exit_code": result.returncode,
            "success": True,
        }

    except subprocess.TimeoutExpired:
        return {
            "output": "Git command timed out",
            "exit_code": 124,
            "success": False,
        }
    except Exception as e:
        return {
            "output": f"Error running git: {str(e)}",
            "exit_code": 1,
            "success": False,
        }
