"""Workspace observer - detects project type, languages, build systems, git state."""

import os
import subprocess


async def inspect(cwd: str = ".") -> dict:
    """Inspect workspace characteristics.

    Re-runs every task as workspace state changes frequently.
    """
    result = {
        "project_type": None,
        "languages": [],
        "build_system": None,
        "test_runner": None,
        "package_manager": None,
        "git": {
            "is_repo": False,
            "branch": None,
            "clean": None,
            "modified_files": [],
        },
        "top_level_files": [],
    }

    try:
        files = os.listdir(cwd)
        result["top_level_files"] = sorted(files[:50])
    except Exception:
        pass

    if "Cargo.toml" in files:
        result["languages"].append("rust")
        result["project_type"] = "rust"
        result["build_system"] = "cargo"
        result["test_runner"] = "cargo"
        result["package_manager"] = "cargo"

    if "package.json" in files:
        result["languages"].append("javascript")
        if not result["project_type"]:
            result["project_type"] = "node"
        result["build_system"] = "npm/yarn/pnpm"

        if "package-lock.json" in files:
            result["package_manager"] = "npm"
        elif "yarn.lock" in files:
            result["package_manager"] = "yarn"
        elif "pnpm-lock.yaml" in files:
            result["package_manager"] = "pnpm"
        elif "bun.lockb" in files:
            result["package_manager"] = "bun"

    if "pyproject.toml" in files or "setup.py" in files or "requirements.txt" in files:
        result["languages"].append("python")
        if not result["project_type"]:
            result["project_type"] = "python"

        if "pyproject.toml" in files:
            result["build_system"] = "poetry/uv"
            result["package_manager"] = "poetry/uv/pip"
        else:
            result["package_manager"] = "pip"

        if "pytest.ini" in files or "pyproject.toml" in files:
            result["test_runner"] = "pytest"

    if "go.mod" in files:
        result["languages"].append("go")
        result["project_type"] = "go"
        result["build_system"] = "go"
        result["test_runner"] = "go test"
        result["package_manager"] = "go"

    if "pom.xml" in files or "build.gradle" in files:
        result["languages"].append("java")
        if not result["project_type"]:
            result["project_type"] = "java"

        if "pom.xml" in files:
            result["build_system"] = "maven"
            result["package_manager"] = "maven"
        elif "build.gradle" in files:
            result["build_system"] = "gradle"
            result["package_manager"] = "gradle"

    if "Makefile" in files:
        result["build_system"] = "make"

    if "CMakeLists.txt" in files:
        result["languages"].append("c/c++")
        result["build_system"] = "cmake"

    try:
        git_check = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            capture_output=True,
            timeout=2,
        )
        result["git"]["is_repo"] = git_check.returncode == 0

        if result["git"]["is_repo"]:
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=2,
            )
            if branch_result.returncode == 0:
                result["git"]["branch"] = branch_result.stdout.strip()

            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=2,
            )
            if status_result.returncode == 0:
                output = status_result.stdout.strip()
                result["git"]["clean"] = len(output) == 0
                if output:
                    result["git"]["modified_files"] = output.split("\n")[:20]

    except Exception:
        pass

    return result
