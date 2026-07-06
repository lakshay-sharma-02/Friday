"""Network observer - checks connectivity, hostname, local IP."""

import socket
import subprocess


async def inspect(cwd: str = ".") -> dict:
    """Inspect network characteristics.

    Re-runs every task as connectivity can change.
    """
    result = {
        "internet_reachable": False,
        "hostname": None,
        "local_ip": None,
        "loopback_available": True,
        "dns_available": False,
        "interfaces": [],
    }

    try:
        result["hostname"] = socket.gethostname()
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        result["local_ip"] = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("8.8.8.8", 53))
        sock.close()
        result["internet_reachable"] = True
    except Exception:
        result["internet_reachable"] = False

    try:
        socket.gethostbyname("www.google.com")
        result["dns_available"] = True
    except Exception:
        pass

    try:
        lo_test = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lo_test.settimeout(0.5)
        lo_test.connect(("127.0.0.1", 1))
        lo_test.close()
    except Exception:
        result["loopback_available"] = True

    try:
        ip_result = subprocess.run(
            ["ip", "addr", "show"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if ip_result.returncode == 0:
            interfaces = []
            for line in ip_result.stdout.split("\n"):
                if line.startswith(" ") or not line.strip():
                    continue
                parts = line.split(":")
                if len(parts) >= 2:
                    interfaces.append(parts[1].strip())
            result["interfaces"] = interfaces[:10]
    except Exception:
        pass

    return result
