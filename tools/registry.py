"""Tool registry - single source of truth for all Friday tools."""

from tools.shell import run_shell, start_shell
from tools.python import run_python, start_python
from tools.process import run_process_tool
from tools.files import read_file, write_file, list_directory, search_files, replace_in_file, diff_files
from tools.git import (
    git_status,
    git_diff,
    git_add,
    git_commit,
    git_log,
    git_branch,
    git_checkout,
    git_restore,
    git_reset,
    git_clone,
)


TOOL_REGISTRY = {
    "shell": {
        "description": "Execute an OS command (no shell interpretation); returns stdout, stderr, exit code, duration, pid",
        "args": {
            "command": {"type": "string", "required": True, "description": "Command string or argv list to execute"},
            "cwd": {"type": "string", "required": False, "description": "Working directory"},
            "timeout": {"type": "integer", "required": False, "description": "Timeout in seconds (default: 30)"},
            "env": {"type": "object", "required": False, "description": "Extra/override environment variables"},
        },
        "handler": run_shell,
    },
    "python": {
        "description": "Run Python via the system interpreter (file or inline script); no special capabilities",
        "args": {
            "file": {"type": "string", "required": False, "description": "Path to .py file to execute"},
            "script": {"type": "string", "required": False, "description": "Inline Python source to run"},
            "args": {"type": "list", "required": False, "description": "Arguments passed to the script"},
            "cwd": {"type": "string", "required": False, "description": "Working directory"},
            "timeout": {"type": "integer", "required": False, "description": "Timeout in seconds (default: 30)"},
        },
        "handler": run_python,
    },
    "start_shell": {
        "description": "Launch an OS command in the background; inspect/terminate it via the process tool",
        "args": {
            "command": {"type": "string", "required": True, "description": "Command string or argv list to execute"},
            "cwd": {"type": "string", "required": False, "description": "Working directory"},
            "env": {"type": "object", "required": False, "description": "Extra/override environment variables"},
        },
        "handler": start_shell,
    },
    "start_python": {
        "description": "Launch Python in the background; inspect/terminate it via the process tool",
        "args": {
            "file": {"type": "string", "required": False, "description": "Path to .py file to execute"},
            "script": {"type": "string", "required": False, "description": "Inline Python source to run"},
            "args": {"type": "list", "required": False, "description": "Arguments passed to the script"},
            "cwd": {"type": "string", "required": False, "description": "Working directory"},
        },
        "handler": start_python,
    },
    "process": {
        "description": "List, inspect, or gracefully terminate processes started by Friday",
        "args": {
            "action": {"type": "string", "required": False, "description": "list | inspect | terminate (default: list)"},
            "pid": {"type": "integer", "required": False, "description": "Target pid for inspect/terminate"},
            "graceful_timeout": {"type": "number", "required": False, "description": "Grace period before SIGKILL (default: 5)"},
        },
        "handler": run_process_tool,
    },
    "read_file": {
        "description": "Read contents of a file",
        "args": {
            "path": {"type": "string", "required": True, "description": "Path to file to read"},
            "start_line": {"type": "integer", "required": False, "description": "Optional start line (1-indexed)"},
            "end_line": {"type": "integer", "required": False, "description": "Optional end line (1-indexed)"},
        },
        "handler": read_file,
    },
    "write_file": {
        "description": "Write content to a file, creating directories if needed",
        "args": {
            "path": {"type": "string", "required": True, "description": "Path to file to write"},
            "content": {"type": "string", "required": True, "description": "Content to write to file"},
            "overwrite": {"type": "boolean", "required": False, "description": "Whether to overwrite existing file (default True)"},
        },
        "handler": write_file,
    },
    "list_directory": {
        "description": "List directory contents",
        "args": {
            "path": {"type": "string", "required": True, "description": "Directory path"},
            "recursive": {"type": "boolean", "required": False, "description": "Whether to list recursively"},
            "include_hidden": {"type": "boolean", "required": False, "description": "Whether to include hidden files (starting with .)"},
            "max_depth": {"type": "integer", "required": False, "description": "Maximum recursion depth"},
            "ignore_patterns": {"type": "list", "required": False, "description": "Glob patterns to ignore"},
        },
        "handler": list_directory,
    },
    "search_files": {
        "description": "Search files for a string or regex",
        "args": {
            "path": {"type": "string", "required": True, "description": "Directory or file to search"},
            "query": {"type": "string", "required": True, "description": "String or regex to search for"},
            "is_regex": {"type": "boolean", "required": False, "description": "Whether query is a regular expression"},
            "context_lines": {"type": "integer", "required": False, "description": "Number of context lines to return"},
        },
        "handler": search_files,
    },
    "replace_in_file": {
        "description": "Replace text in a file",
        "args": {
            "path": {"type": "string", "required": True, "description": "File to modify"},
            "search": {"type": "string", "required": True, "description": "String or regex to search for"},
            "replace": {"type": "string", "required": True, "description": "Replacement string"},
            "is_regex": {"type": "boolean", "required": False, "description": "Whether search is a regex"},
            "preview": {"type": "boolean", "required": False, "description": "If True, do not actually write changes"},
        },
        "handler": replace_in_file,
    },
    "diff_files": {
        "description": "Compute unified diff of two files",
        "args": {
            "path1": {"type": "string", "required": True, "description": "First file path"},
            "path2": {"type": "string", "required": True, "description": "Second file path"},
        },
        "handler": diff_files,
    },
    "git_status": {
        "description": "Inspect git repo: branch, clean/dirty, staged/modified/untracked/conflicted, ahead/behind",
        "args": {
            "repo_path": {"type": "string", "required": False, "description": "Repo directory (default: cwd)"},
        },
        "handler": git_status,
    },
    "git_diff": {
        "description": "Unified diff with file/insertion/deletion summary; optional file or staged",
        "args": {
            "file": {"type": "string", "required": False, "description": "Restrict diff to one file"},
            "staged": {"type": "boolean", "required": False, "description": "Diff staged changes instead of working tree"},
            "cwd": {"type": "string", "required": False, "description": "Repo directory"},
        },
        "handler": git_diff,
    },
    "git_add": {
        "description": "Stage files for commit",
        "args": {
            "paths": {"type": "list", "required": False, "description": "Files to stage"},
            "all": {"type": "boolean", "required": False, "description": "Stage everything (git add -A)"},
            "cwd": {"type": "string", "required": False, "description": "Repo directory"},
        },
        "handler": git_add,
    },
    "git_commit": {
        "description": "Create a commit (refuses empty by default); returns hash/author/timestamp/summary",
        "args": {
            "message": {"type": "string", "required": True, "description": "Commit message"},
            "cwd": {"type": "string", "required": False, "description": "Repo directory"},
            "allow_empty": {"type": "boolean", "required": False, "description": "Allow empty commit"},
        },
        "handler": git_commit,
    },
    "git_log": {
        "description": "List recent commits with hash, author, date, message",
        "args": {
            "limit": {"type": "integer", "required": False, "description": "Max commits (default 10)"},
            "oneline": {"type": "boolean", "required": False, "description": "One-line mode"},
            "cwd": {"type": "string", "required": False, "description": "Repo directory"},
        },
        "handler": git_log,
    },
    "git_branch": {
        "description": "List/create/delete/rename branches",
        "args": {
            "name": {"type": "string", "required": False, "description": "Branch name (create/delete/rename)"},
            "action": {"type": "string", "required": False, "description": "list|create|delete|rename (default list)"},
            "old": {"type": "string", "required": False, "description": "Old name for rename"},
            "confirm": {"type": "boolean", "required": False, "description": "Required for delete"},
            "cwd": {"type": "string", "required": False, "description": "Repo directory"},
        },
        "handler": git_branch,
    },
    "git_checkout": {
        "description": "Switch/create branch; detects detached HEAD; dirty tree requires confirm",
        "args": {
            "target": {"type": "string", "required": True, "description": "Branch or commit to checkout"},
            "create": {"type": "boolean", "required": False, "description": "Create branch (-b)"},
            "confirm": {"type": "boolean", "required": False, "description": "Required for dirty working tree"},
            "cwd": {"type": "string", "required": False, "description": "Repo directory"},
        },
        "handler": git_checkout,
    },
    "git_restore": {
        "description": "Restore working-tree/staged files; preview=True or confirm=True required",
        "args": {
            "paths": {"type": "list", "required": True, "description": "Files to restore"},
            "staged": {"type": "boolean", "required": False, "description": "Restore staged (--staged)"},
            "working_tree": {"type": "boolean", "required": False, "description": "Restore working tree (default True unless staged only)"},
            "preview": {"type": "boolean", "required": False, "description": "Dry-run"},
            "confirm": {"type": "boolean", "required": False, "description": "Required to actually discard work"},
            "cwd": {"type": "string", "required": False, "description": "Repo directory"},
        },
        "handler": git_restore,
    },
    "git_reset": {
        "description": "Reset to a target. Supports --soft and --mixed only (never --hard). confirm=True required",
        "args": {
            "mode": {"type": "string", "required": False, "description": "soft|mixed (default mixed)"},
            "target": {"type": "string", "required": False, "description": "Reset target (default HEAD)"},
            "confirm": {"type": "boolean", "required": True, "description": "Required to perform reset"},
            "cwd": {"type": "string", "required": False, "description": "Repo directory"},
        },
        "handler": git_reset,
    },
    "git_clone": {
        "description": "Clone a repository by URL into an optional target dir",
        "args": {
            "url": {"type": "string", "required": True, "description": "Repository URL"},
            "target_dir": {"type": "string", "required": False, "description": "Directory to clone into"},
            "cwd": {"type": "string", "required": False, "description": "Base directory"},
        },
        "handler": git_clone,
    },
}
