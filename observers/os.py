"""OS observer - platform, shell, PATH, environment variables with secret filtering."""

import os
import platform
import subprocess


SECRET_KEYWORDS = [
    "key",
    "token",
    "secret",
    "password",
    "passwd",
    "credential",
    "auth",
    "apikey",
    "access",
]


def _should_redact(var_name: str) -> bool:
    """Check if an environment variable name contains secret-related keywords."""
    lower_name = var_name.lower()
    return any(keyword in lower_name for keyword in SECRET_KEYWORDS)


async def inspect(cwd: str = ".") -> dict:
    """Inspect OS characteristics.

    Near-static data, cached for 5 minutes by environment_manager.
    """
    result = {
        "platform": None,
        "version": None,
        "shell": None,
        "path_summary": [],
        "home_directory": None,
        "environment_variables": {},
        "cwd": None,
        "temp_directory": None,
    }

    try:
        result["platform"] = platform.system()
    except Exception:
        pass

    try:
        result["version"] = platform.version()
    except Exception:
        pass

    try:
        result["shell"] = os.getenv("SHELL")
    except Exception:
        pass

    try:
        result["home_directory"] = os.path.expanduser("~")
    except Exception:
        pass

    try:
        result["cwd"] = os.getcwd()
    except Exception:
        pass

    try:
        result["temp_directory"] = os.getenv("TMPDIR") or os.getenv("TEMP") or "/tmp"
    except Exception:
        pass

    try:
        path_env = os.getenv("PATH", "")
        paths = path_env.split(":")
        result["path_summary"] = paths[:20]
    except Exception:
        pass

    try:
        useful_vars = [
            "USER",
            "HOME",
            "SHELL",
            "PATH",
            "LANG",
            "TERM",
            "EDITOR",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GITHUB_TOKEN",
            "DOCKER_HOST",
            "PYTHONPATH",
            "NODE_ENV",
            "RUST_LOG",
            "GO_ENV",
        ]

        for var in useful_vars:
            value = os.getenv(var)
            if value is not None:
                if _should_redact(var):
                    result["environment_variables"][var] = "[REDACTED]"
                else:
                    result["environment_variables"][var] = value[:200]

    except Exception:
        pass

    return result
