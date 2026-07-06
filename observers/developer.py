"""Developer observer - detects tool availability and versions."""

import subprocess


async def inspect(cwd: str = ".") -> dict:
    """Inspect developer tool availability and versions.

    Near-static data, cached for 5 minutes by environment_manager.
    """
    tools = [
        "git",
        "python",
        "pip",
        "uv",
        "poetry",
        "node",
        "npm",
        "pnpm",
        "yarn",
        "bun",
        "cargo",
        "rustc",
        "go",
        "gcc",
        "clang",
        "cmake",
        "docker",
        "kubectl",
        "java",
    ]

    result = {}

    for tool in tools:
        try:
            version_result = subprocess.run(
                [tool, "--version"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if version_result.returncode == 0:
                version_line = version_result.stdout.split("\n")[0]
                result[tool] = {
                    "available": True,
                    "version": version_line[:100],
                }
            else:
                result[tool] = {"available": False, "version": None}
        except FileNotFoundError:
            result[tool] = {"available": False, "version": None}
        except Exception:
            result[tool] = {"available": False, "version": None}

    return result
