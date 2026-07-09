"""Git tools for Friday.

Thin, validated wrappers around the `git` executable. Every git invocation goes
through the shared execution layer (`run_shell` -> `process_manager`), so timeout,
cancellation, and error handling stay centralized and consistent with the other
execution tools. No handler prints. Destructive operations require an explicit
`confirm=True`.
"""

from tools.shell import run_shell

GIT_TIMEOUT = 30


def _git(args, cwd=None, timeout=GIT_TIMEOUT) -> dict:
    """Run a git command via the shared execution layer. Never raises."""
    import shlex
    if isinstance(args, list):
        cmd = "git " + " ".join(shlex.quote(str(arg)) for arg in args)
    else:
        cmd = f"git {args}"
    result = run_shell(cmd, cwd=cwd, timeout=timeout)
    exit_code = result.get("exit_code")
    stderr = result.get("stderr", "") or ""
    output = (result.get("stdout", "") or "").strip()
    if stderr:
        output = (output + "\n" + stderr.strip()).strip() or output

    if "spawn failed" in (result.get("reason") or ""):
        return {"success": False, "exit_code": None,
                "output": "", "reason": "git executable not found"}

    if exit_code == 128 and "not a git repository" in output.lower():
        return {"success": False, "exit_code": 128,
                "output": "", "reason": "not a git repository", "is_repo": False}

    return {
        "success": result.get("success", False),
        "exit_code": exit_code,
        "output": output,
        "reason": None if result.get("success") else (stderr or result.get("reason") or "git failed"),
        "is_repo": True,
    }


def git_status(repo_path=None) -> dict:
    """Inspect working tree state of a Git repository."""
    res = _git(["status", "--porcelain=v2", "--branch"], cwd=repo_path)
    if not res["success"]:
        res.setdefault("is_repo", True)
        return res

    branch = None
    ahead = behind = 0
    staged, modified, untracked, conflicted = [], [], [], []

    for line in res["output"].splitlines():
        if line.startswith("# branch.head "):
            branch = line[len("# branch.head "):].strip()
            if branch == "(detached)":
                branch = None
        elif line.startswith("# branch.ab "):
            ab = line[len("# branch.ab "):].strip()
            parts = ab.split()
            if len(parts) == 2:
                ahead = int(parts[0].lstrip("+").lstrip("-") or 0)
                behind = int(parts[1].lstrip("+").lstrip("-") or 0)
        elif not line.startswith("#") and len(line) >= 2:
            fields = line.split()
            if fields[0] == "?":
                untracked.append(fields[1])
                continue
            # porcelain v2 track line: "<ordinal> <XY> <mode>... <path>"
            # XY is field index 1 (field 0 is the ordinal/index tag).
            xy = fields[1]
            x, y = xy[0], xy[1]
            path = fields[-1]
            # X = HEAD-vs-index (staged), Y = index-vs-worktree (modified).
            # '.' means "no change" in that column; only letters are changes.
            if x not in (" ", ".", "?"):
                staged.append(path)
            if y not in (" ", "."):
                modified.append(path)
            if (x, y) in (("D", "D"), ("A", "U"), ("U", "D"), ("U", "A"),
                          ("D", "U"), ("A", "A"), ("U", "U")):
                conflicted.append(path)

    return {
        "success": True,
        "is_repo": True,
        "branch": branch,
        "detached_head": branch is None,
        "clean": not (staged or modified or untracked or conflicted),
        "staged": staged,
        "modified": modified,
        "untracked": untracked,
        "conflicted": conflicted,
        "ahead": ahead,
        "behind": behind,
        "output": res["output"],
    }


def git_diff(file=None, staged=False, cwd=None) -> dict:
    """Show a unified diff (optionally for one file/staged) plus a summary."""
    diff_args = ["diff"]
    if staged:
        diff_args.append("--staged")
    if file:
        diff_args += ["--", file]

    res = _git(diff_args, cwd=cwd)
    if not res["success"]:
        return res

    numstat = _git(diff_args + ["--numstat"], cwd=cwd)
    files_changed = insertions = deletions = 0
    if numstat["success"]:
        for line in numstat["output"].splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and parts[0] != "-":
                files_changed += 1
                try:
                    insertions += int(parts[0])
                    deletions += int(parts[1])
                except ValueError:
                    pass

    return {
        "success": True,
        "is_repo": True,
        "diff": res["output"],
        "files_changed": files_changed,
        "insertions": insertions,
        "deletions": deletions,
        "output": res["output"] or "(no changes)",
    }


def git_add(paths=None, all=False, cwd=None) -> dict:
    """Stage files. Provide a list of paths or all=True."""
    if all:
        args = ["add", "-A"]
    elif paths:
        args = ["add", "--", *([paths] if isinstance(paths, str) else paths)]
    else:
        return {"success": False, "exit_code": None,
                "output": "", "reason": "specify paths or all=True"}

    res = _git(args, cwd=cwd)
    if res["success"]:
        res["output"] = "staged" + (f" {paths}" if not all else " all")
    return res


def git_commit(message, cwd=None, allow_empty=False) -> dict:
    """Create a commit. Refuses empty commits unless allow_empty=True."""
    if not message or not message.strip():
        return {"success": False, "exit_code": None,
                "output": "", "reason": "commit message required"}

    staged = _git(["diff", "--cached", "--quiet"], cwd=cwd)
    if staged["exit_code"] == 0 and not allow_empty:
        return {"success": False, "exit_code": 1,
                "output": "", "reason": "nothing staged to commit (empty commit)"}

    res = _git(["commit", "-m", message], cwd=cwd)
    if not res["success"]:
        return res

    info = _git(["log", "-1", "--format=%H%x1f%an <%ae>%x1f%aI%x1f%s"], cwd=cwd)
    if info["success"]:
        h, author, ts, summary = (info["output"].split("\x1f") + ["", "", "", ""])[:4]
        return {
            "success": True,
            "is_repo": True,
            "commit_hash": h,
            "author": author,
            "timestamp": ts,
            "summary": summary,
            "output": f"committed {h[:8]}: {summary}",
        }
    return res


def git_log(limit=10, oneline=False, cwd=None) -> dict:
    """List recent commits."""
    fmt = "%H%x1f%an <%ae>%x1f%aI%x1f%s" if not oneline else "%H %s"
    res = _git(["log", f"-{limit}", f"--format={fmt}"], cwd=cwd)
    if not res["success"]:
        return res

    commits = []
    for entry in res["output"].splitlines():
        if not entry.strip():
            continue
        if oneline:
            h, _, msg = entry.partition(" ")
            commits.append({"hash": h, "message": msg})
        else:
            h, author, ts, summary = (entry.split("\x1f") + ["", "", "", ""])[:4]
            commits.append({"hash": h, "author": author, "date": ts, "message": summary})

    return {"success": True, "is_repo": True, "commits": commits,
            "count": len(commits), "output": res["output"] or "(no commits)"}


def git_branch(name=None, action="list", old=None, cwd=None, confirm=False) -> dict:
    """List, create, delete, or rename branches."""
    action = (action or "list").lower()

    if action == "list":
        res = _git(["branch", "--format=%(refname:short)"], cwd=cwd)
        if not res["success"]:
            return res
        branches = res["output"].splitlines()
        current = None
        cur = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
        if cur["success"]:
            current = cur["output"].strip()
            if current == "HEAD":
                current = None
        return {"success": True, "is_repo": True, "branches": branches,
                "current": current, "count": len(branches),
                "output": res["output"] or "(no branches)"}

    if action == "create":
        if not name:
            return {"success": False, "exit_code": None,
                    "output": "", "reason": "branch name required"}
        res = _git(["branch", name], cwd=cwd)
        if res["success"]:
            res["output"] = f"created branch {name}"
        return res

    if action == "delete":
        if not name:
            return {"success": False, "exit_code": None,
                    "output": "", "reason": "branch name required"}
        if not confirm:
            return {"success": False, "exit_code": None,
                    "output": "", "reason": "branch deletion requires confirm=True",
                    "needs_confirm": True}
        res = _git(["branch", "-d", name], cwd=cwd)
        if res["success"]:
            res["output"] = f"deleted branch {name}"
        return res

    if action == "rename":
        if not name:
            return {"success": False, "exit_code": None,
                    "output": "", "reason": "new branch name required"}
        args = ["branch", "-m", name] if not old else ["branch", "-m", old, name]
        res = _git(args, cwd=cwd)
        if res["success"]:
            res["output"] = f"renamed to {name}"
        return res

    return {"success": False, "exit_code": None,
            "output": "", "reason": f"unknown branch action '{action}'"}


def git_checkout(target, create=False, cwd=None, confirm=False) -> dict:
    """Switch branches, optionally creating a new one."""
    if not target:
        return {"success": False, "exit_code": None,
                "output": "", "reason": "checkout target required"}

    if not create and not confirm:
        st = git_status(cwd)
        if st.get("success") and not st.get("clean", True):
            return {"success": False, "exit_code": None,
                    "output": "", "reason": "working tree dirty; checkout requires confirm=True",
                    "needs_confirm": True}

    args = ["checkout"]
    if create:
        args.append("-b")
    args.append(target)

    res = _git(args, cwd=cwd)
    if not res["success"]:
        return res

    head = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    detached = head.get("output", "").strip() == "HEAD"
    res["detached_head"] = detached
    res["branch"] = None if detached else head.get("output", "").strip()
    res["output"] = f"checked out {target}" + (" (detached HEAD)" if detached else "")
    return res


def git_restore(paths, staged=False, working_tree=None, preview=False,
                cwd=None, confirm=False) -> dict:
    """Restore working-tree and/or staged files. Destructive without preview.

    working_tree defaults to True unless staged=True is requested alone (then
    only the index is restored).
    """
    if not paths:
        return {"success": False, "exit_code": None,
                "output": "", "reason": "paths required"}
    if working_tree is None:
        working_tree = not staged
    if not staged and not working_tree:
        return {"success": False, "exit_code": None,
                "output": "", "reason": "specify staged and/or working_tree"}

    if not preview and not confirm:
        return {"success": False, "exit_code": None,
                "output": "", "reason": "restore discards work; set preview=True or confirm=True",
                "needs_confirm": True}

    if preview:
        # git restore has no dry-run; preview by showing the diff that would
        # be discarded (unstaged working-tree diff, or staged diff).
        diff_args = ["diff"]
        if staged and not working_tree:
            diff_args.append("--cached")
        diff_args += ["--", *([paths] if isinstance(paths, str) else paths)]
        d = _git(diff_args, cwd=cwd)
        return {
            "success": d.get("success", False),
            "is_repo": d.get("is_repo", True),
            "preview": True,
            "output": "would restore (changes that would be discarded):\n"
                      + (d.get("output") or "(no diff)"),
        }

    args = ["restore"]
    if staged and not working_tree:
        args.append("--staged")
    elif working_tree and not staged:
        args.append("--worktree")
    args += ["--", *([paths] if isinstance(paths, str) else paths)]

    res = _git(args, cwd=cwd)
    if res["success"]:
        res["output"] = "restored " + str(paths)
    return res


def git_reset(mode="mixed", target="HEAD", cwd=None, confirm=False) -> dict:
    """Reset to target. Supports --soft and --mixed only (never --hard)."""
    if mode not in ("soft", "mixed"):
        return {"success": False, "exit_code": None,
                "output": "", "reason": "only --soft and --mixed are supported"}

    if not confirm:
        return {"success": False, "exit_code": None,
                "output": "", "reason": "reset requires confirm=True",
                "needs_confirm": True}

    res = _git(["reset", f"--{mode}", target], cwd=cwd)
    if res["success"]:
        res["output"] = f"reset ({mode}) to {target}"
    return res


def git_clone(url, target_dir=None, cwd=None) -> dict:
    """Clone a repository by URL."""
    if not url or not str(url).strip():
        return {"success": False, "exit_code": None,
                "output": "", "reason": "repository URL required"}

    args = ["clone", url]
    if target_dir:
        args.append(target_dir)

    res = _git(args, cwd=cwd, timeout=120)
    if res["success"]:
        res["output"] = f"cloned {url}"
    return res
