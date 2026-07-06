"""File operations."""

import os
import re
import difflib
import tempfile
import fnmatch
from pathlib import Path
from typing import Optional, List, Dict, Any


def is_binary(file_path: str) -> bool:
    """Check if file is binary by reading the first chunk."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:
                return True
            chunk.decode('utf-8')
            return False
    except UnicodeDecodeError:
        return True
    except Exception:
        return False


def read_file(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> dict:
    """Read a file and return its contents.

    Args:
        path: Path to file to read
        start_line: Optional start line (1-indexed)
        end_line: Optional end line (1-indexed)

    Returns:
        Dict with output, exit_code, success fields, and metadata
    """
    if start_line is not None and start_line < 1:
        raise ValueError("start_line must be >= 1")
    if start_line is not None and end_line is not None and start_line > end_line:
        raise ValueError("start_line must be <= end_line")

    try:
        p = Path(path)
        if not p.exists():
            return {"output": f"File not found: {path}", "exit_code": 2, "success": False}
        if p.is_dir():
            return {"output": f"Is a directory: {path}", "exit_code": 21, "success": False}

        stat = p.stat()
        metadata = {
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }

        if is_binary(path):
            return {
                "output": f"Cannot read binary file: {path}",
                "exit_code": 1,
                "success": False,
                "metadata": metadata
            }

        with open(path, "r", encoding="utf-8") as f:
            if start_line is None and end_line is None:
                content = f.read()
            else:
                lines = f.readlines()
                start_idx = max(0, start_line - 1) if start_line is not None else 0
                end_idx = min(len(lines), end_line) if end_line is not None else len(lines)
                content = "".join(lines[start_idx:end_idx])

        return {
            "output": content,
            "exit_code": 0,
            "success": True,
            "metadata": metadata
        }
    except PermissionError:
        return {"output": f"Permission denied: {path}", "exit_code": 13, "success": False}
    except Exception as e:
        return {"output": f"Error reading file: {str(e)}", "exit_code": 1, "success": False}


def write_file(path: str, content: str, overwrite: bool = True) -> dict:
    """Write content to a file.

    Args:
        path: Path to file to write
        content: Content to write
        overwrite: Whether to overwrite existing file

    Returns:
        Dict with output and success fields
    """
    if not isinstance(path, str):
        raise ValueError("path must be a string")
        
    try:
        p = Path(path)
        if p.exists() and not overwrite:
            return {"output": f"File exists and overwrite is False: {path}", "exit_code": 1, "success": False}
            
        p.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write
        fd, temp_path = tempfile.mkstemp(dir=p.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(temp_path, path)
        except Exception:
            os.remove(temp_path)
            raise

        return {
            "output": f"Wrote {len(content.encode('utf-8'))} bytes to {path}",
            "exit_code": 0,
            "success": True,
        }

    except PermissionError:
        return {"output": f"Permission denied: {path}", "exit_code": 13, "success": False}
    except Exception as e:
        return {"output": f"Error writing file: {str(e)}", "exit_code": 1, "success": False}


def _should_ignore(path: str, ignore_patterns: List[str]) -> bool:
    name = os.path.basename(path)
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False

def list_directory(path: str, recursive: bool = False, include_hidden: bool = False, max_depth: Optional[int] = None, ignore_patterns: Optional[List[str]] = None) -> dict:
    """List directory contents.
    
    Args:
        path: Directory path
        recursive: Whether to list recursively
        include_hidden: Whether to include hidden files (starting with .)
        max_depth: Maximum recursion depth
        ignore_patterns: Glob patterns to ignore
    """
    if max_depth is not None and max_depth < 0:
        raise ValueError("max_depth must be >= 0")
        
    try:
        p = Path(path)
        if not p.exists():
            return {"output": f"Directory not found: {path}", "exit_code": 2, "success": False}
        if not p.is_dir():
            return {"output": f"Not a directory: {path}", "exit_code": 20, "success": False}

        ignores = ignore_patterns or []
        results = []
        
        def walk(current_dir: Path, current_depth: int):
            if max_depth is not None and current_depth > max_depth:
                return
                
            try:
                for entry in current_dir.iterdir():
                    if not include_hidden and entry.name.startswith('.'):
                        continue
                    if _should_ignore(str(entry), ignores):
                        continue
                        
                    stat = entry.stat()
                    item = {
                        "name": entry.name,
                        "path": str(entry.relative_to(p)) if current_depth > 0 else entry.name,
                        "is_dir": entry.is_dir(),
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    }
                    results.append(item)
                    
                    if recursive and entry.is_dir():
                        walk(entry, current_depth + 1)
            except PermissionError:
                pass

        walk(p, 0)
        
        return {
            "output": f"Found {len(results)} items",
            "files": results,
            "exit_code": 0,
            "success": True,
        }
    except Exception as e:
        return {"output": f"Error listing directory: {str(e)}", "exit_code": 1, "success": False}


def search_files(path: str, query: str, is_regex: bool = False, context_lines: int = 0) -> dict:
    """Search files for a string or regex.
    
    Args:
        path: Directory or file to search
        query: String or regex to search for
        is_regex: Whether query is a regular expression
        context_lines: Number of context lines to return
    """
    if context_lines < 0:
        raise ValueError("context_lines must be >= 0")
        
    try:
        p = Path(path)
        if not p.exists():
            return {"output": f"Path not found: {path}", "exit_code": 2, "success": False}

        ignores = ['.git', 'node_modules', '__pycache__']
        results = []
        
        if is_regex:
            try:
                pattern = re.compile(query)
            except re.error as e:
                raise ValueError(f"Invalid regex: {e}")
        else:
            pattern = None
            
        def search_file(file_path: Path):
            if is_binary(str(file_path)):
                return
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                matches = []
                for i, line in enumerate(lines):
                    is_match = False
                    if is_regex and pattern:
                        is_match = bool(pattern.search(line))
                    elif not is_regex:
                        is_match = query in line
                        
                    if is_match:
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        context = "".join(lines[start:end])
                        matches.append({
                            "line_number": i + 1,
                            "match": line.rstrip('\n'),
                            "context": context
                        })
                
                if matches:
                    results.append({
                        "file": str(file_path),
                        "matches": matches
                    })
            except Exception:
                pass

        def walk(current_dir: Path):
            try:
                for entry in current_dir.iterdir():
                    if _should_ignore(str(entry), ignores):
                        continue
                    if entry.is_dir():
                        walk(entry)
                    else:
                        search_file(entry)
            except Exception:
                pass

        if p.is_dir():
            walk(p)
        else:
            search_file(p)
            
        total_matches = sum(len(f["matches"]) for f in results)
        return {
            "output": f"Found {total_matches} matches in {len(results)} files",
            "results": results,
            "exit_code": 0,
            "success": True,
        }
    except ValueError:
        raise
    except Exception as e:
        return {"output": f"Error searching files: {str(e)}", "exit_code": 1, "success": False}


def replace_in_file(path: str, search: str, replace: str, is_regex: bool = False, preview: bool = False) -> dict:
    """Replace text in a file.
    
    Args:
        path: File to modify
        search: String or regex to search for
        replace: Replacement string
        is_regex: Whether search is a regex
        preview: If True, do not actually write changes
    """
    if not isinstance(path, str):
        raise ValueError("path must be a string")
        
    try:
        p = Path(path)
        if not p.exists():
            return {"output": f"File not found: {path}", "exit_code": 2, "success": False}
        if p.is_dir():
            return {"output": f"Is a directory: {path}", "exit_code": 21, "success": False}
        if is_binary(str(path)):
            return {"output": f"Cannot modify binary file: {path}", "exit_code": 1, "success": False}

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if is_regex:
            try:
                pattern = re.compile(search)
            except re.error as e:
                raise ValueError(f"Invalid regex: {e}")
            new_content, count = pattern.subn(replace, content)
        else:
            count = content.count(search)
            new_content = content.replace(search, replace)

        if not preview and count > 0:
            fd, temp_path = tempfile.mkstemp(dir=p.parent)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                os.replace(temp_path, path)
            except Exception:
                os.remove(temp_path)
                raise

        return {
            "output": f"Replaced {count} occurrences",
            "replacements": count,
            "exit_code": 0,
            "success": True,
        }
    except ValueError:
        raise
    except PermissionError:
        return {"output": f"Permission denied: {path}", "exit_code": 13, "success": False}
    except Exception as e:
        return {"output": f"Error replacing in file: {str(e)}", "exit_code": 1, "success": False}


def diff_files(path1: str, path2: str) -> dict:
    """Compute unified diff of two files.
    
    Args:
        path1: First file path
        path2: Second file path
    """
    if not isinstance(path1, str) or not isinstance(path2, str):
        raise ValueError("paths must be strings")
        
    try:
        p1 = Path(path1)
        p2 = Path(path2)
        
        if not p1.exists():
            return {"output": f"File not found: {path1}", "exit_code": 2, "success": False}
        if not p2.exists():
            return {"output": f"File not found: {path2}", "exit_code": 2, "success": False}
            
        if is_binary(str(p1)) or is_binary(str(p2)):
            return {"output": "Cannot diff binary files", "exit_code": 1, "success": False}
            
        with open(p1, 'r', encoding='utf-8') as f1, open(p2, 'r', encoding='utf-8') as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()
            
        diff = list(difflib.unified_diff(
            lines1, lines2, 
            fromfile=str(p1), tofile=str(p2)
        ))
        
        added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        return {
            "output": "".join(diff) if diff else "Files are identical",
            "diff": "".join(diff),
            "added_lines": added,
            "removed_lines": removed,
            "exit_code": 0 if not diff else 1,
            "success": True,
        }
    except Exception as e:
        return {"output": f"Error comparing files: {str(e)}", "exit_code": 1, "success": False}
