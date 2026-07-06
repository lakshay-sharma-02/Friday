"""Tool registry - single source of truth for all Friday tools."""

from tools.shell import run_shell
from tools.files import read_file, write_file, list_directory, search_files, replace_in_file, diff_files
from tools.git import git_status


TOOL_REGISTRY = {
    "shell": {
        "description": "Execute a shell command and return output, exit code, and success status",
        "args": {
            "command": {"type": "string", "required": True, "description": "Shell command to execute"},
            "timeout": {"type": "integer", "required": False, "description": "Timeout in seconds (default: 30)"},
        },
        "handler": run_shell,
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
        "description": "Check git repository status for uncommitted changes",
        "args": {},
        "handler": git_status,
    },
}
