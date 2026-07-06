"""Computer observer - OS, CPU, RAM, disk, GPU details."""

import os
import platform
import subprocess
import sys


async def inspect(cwd: str = ".") -> dict:
    """Inspect computer characteristics.

    Near-static data, cached for 5 minutes by environment_manager.
    """
    result = {
        "os": None,
        "cpu": None,
        "logical_cores": None,
        "ram_gb": None,
        "disk_usage": {},
        "gpu": None,
        "battery": None,
        "hostname": None,
        "architecture": None,
        "python_version": None,
        "current_user": None,
    }

    try:
        result["os"] = platform.system()
    except Exception:
        pass

    try:
        result["architecture"] = platform.machine()
    except Exception:
        pass

    try:
        result["hostname"] = platform.node()
    except Exception:
        pass

    try:
        result["python_version"] = sys.version.split()[0]
    except Exception:
        pass

    try:
        result["current_user"] = os.getenv("USER") or os.getenv("USERNAME")
    except Exception:
        pass

    try:
        result["logical_cores"] = os.cpu_count()
    except Exception:
        pass

    try:
        cpu_info = subprocess.run(
            ["lscpu"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if cpu_info.returncode == 0:
            for line in cpu_info.stdout.split("\n"):
                if "Model name:" in line:
                    result["cpu"] = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass

    try:
        mem_info = subprocess.run(
            ["free", "-g"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if mem_info.returncode == 0:
            lines = mem_info.stdout.split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) > 1:
                    result["ram_gb"] = int(parts[1])
    except Exception:
        pass

    try:
        disk_info = subprocess.run(
            ["df", "-h", "."],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if disk_info.returncode == 0:
            lines = disk_info.stdout.split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    result["disk_usage"] = {
                        "total": parts[1],
                        "used": parts[2],
                        "available": parts[3],
                        "use_percent": parts[4],
                    }
    except Exception:
        pass

    try:
        gpu_info = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if gpu_info.returncode == 0 and gpu_info.stdout.strip():
            result["gpu"] = gpu_info.stdout.strip()
    except Exception:
        pass

    try:
        battery_info = subprocess.run(
            ["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if battery_info.returncode == 0:
            for line in battery_info.stdout.split("\n"):
                if "percentage:" in line:
                    result["battery"] = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass

    return result
