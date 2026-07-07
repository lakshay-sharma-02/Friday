"""Deterministic tests for Phase 6C Git tools using temporary repositories."""

import os
import subprocess
import textwrap

import pytest

from tools import git as G


@pytest.fixture
def repo(tmp_path):
    """A fresh git repo with one committed file and a configured identity."""
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.email", "test@friday.local"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.name", "Friday Test"], cwd=r, check=True)
    (r / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "file.txt"], cwd=r, check=True)
    subprocess.run(["git", "commit", "-qm", "initial commit"], cwd=r, check=True)
    return r


def _run(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


# --- status variants ---

def test_status_clean(repo):
    s = G.git_status(repo)
    assert s["success"] is True
    assert s["is_repo"] is True
    assert s["clean"] is True
    assert s["branch"] is not None
    assert s["untracked"] == []
    assert s["staged"] == []


def test_status_dirty(repo):
    (repo / "file.txt").write_text("changed\n")
    (repo / "new.txt").write_text("new\n")
    s = G.git_status(repo)
    assert s["success"] is True
    assert s["clean"] is False
    assert "file.txt" in s["modified"]
    assert "new.txt" in s["untracked"]


def test_status_not_a_repo(tmp_path):
    s = G.git_status(tmp_path)
    assert s["success"] is False
    assert s["is_repo"] is False
    assert s["reason"] == "not a git repository"


# --- diff ---

def test_diff_working_tree(repo):
    (repo / "file.txt").write_text("hello\nworld\n")
    d = G.git_diff(cwd=repo)
    assert d["success"] is True
    assert "+world" in d["diff"]
    assert d["files_changed"] >= 1
    assert d["insertions"] >= 1


def test_diff_staged(repo):
    (repo / "file.txt").write_text("hello\nstaged\n")
    _run(repo, "add", "file.txt")
    d = G.git_diff(staged=True, cwd=repo)
    assert d["success"] is True
    assert "+staged" in d["diff"]
    assert d["files_changed"] == 1


def test_diff_file_specific(repo):
    (repo / "file.txt").write_text("hello\nx\n")
    d = G.git_diff(file="file.txt", cwd=repo)
    assert d["success"] is True
    assert "file.txt" in d["diff"]


# --- add ---

def test_add_single(repo):
    (repo / "a.txt").write_text("a\n")
    r = G.git_add(paths=["a.txt"], cwd=repo)
    assert r["success"] is True
    s = G.git_status(repo)
    assert "a.txt" in s["staged"]


def test_add_multiple(repo):
    (repo / "a.txt").write_text("a\n")
    (repo / "b.txt").write_text("b\n")
    r = G.git_add(paths=["a.txt", "b.txt"], cwd=repo)
    assert r["success"] is True
    s = G.git_status(repo)
    assert set(["a.txt", "b.txt"]).issubset(set(s["staged"]))


def test_add_all(repo):
    (repo / "a.txt").write_text("a\n")
    (repo / "b.txt").write_text("b\n")
    r = G.git_add(all=True, cwd=repo)
    assert r["success"] is True
    s = G.git_status(repo)
    assert "a.txt" in s["staged"] and "b.txt" in s["staged"]


# --- commit ---

def test_commit_success(repo):
    (repo / "a.txt").write_text("a\n")
    G.git_add(paths=["a.txt"], cwd=repo)
    c = G.git_commit("add a.txt", cwd=repo)
    assert c["success"] is True
    assert c["commit_hash"]
    assert len(c["commit_hash"]) == 40
    assert c["author"] == "Friday Test <test@friday.local>"
    assert c["summary"] == "add a.txt"
    assert G.git_status(repo)["clean"] is True


def test_commit_empty_rejected(repo):
    c = G.git_commit("nothing staged", cwd=repo)
    assert c["success"] is False
    assert "nothing staged" in c["reason"]


def test_commit_requires_message(repo):
    c = G.git_commit("", cwd=repo)
    assert c["success"] is False
    assert "message required" in c["reason"]


# --- log ---

def test_log_default(repo):
    (repo / "a.txt").write_text("a\n")
    G.git_add(paths=["a.txt"], cwd=repo)
    G.git_commit("second commit", cwd=repo)
    lg = G.git_log(cwd=repo)
    assert lg["success"] is True
    assert lg["count"] >= 2
    first = lg["commits"][0]
    assert first["hash"] and first["author"] and first["message"]


def test_log_oneline(repo):
    lg = G.git_log(oneline=True, cwd=repo)
    assert lg["success"] is True
    assert lg["commits"][0]["hash"] and "message" in lg["commits"][0]


def test_log_limit(repo):
    for i in range(3):
        (repo / f"f{i}.txt").write_text(f"{i}\n")
        G.git_add(all=True, cwd=repo)
        G.git_commit(f"commit {i}", cwd=repo)
    lg = G.git_log(limit=2, cwd=repo)
    assert lg["count"] == 2


# --- branch ---

def test_branch_list(repo):
    b = G.git_branch(cwd=repo)
    assert b["success"] is True
    assert b["current"] in b["branches"]


def test_branch_create(repo):
    b = G.git_branch(name="feature", action="create", cwd=repo)
    assert b["success"] is True
    assert "feature" in G.git_branch(cwd=repo)["branches"]


def test_branch_delete_requires_confirm(repo):
    G.git_branch(name="feature", action="create", cwd=repo)
    refused = G.git_branch(name="feature", action="delete", cwd=repo)
    assert refused["success"] is False
    assert refused["needs_confirm"] is True
    # With confirm, it succeeds
    done = G.git_branch(name="feature", action="delete", confirm=True, cwd=repo)
    assert done["success"] is True
    assert "feature" not in G.git_branch(cwd=repo)["branches"]


def test_branch_rename(repo):
    G.git_branch(name="old", action="create", cwd=repo)
    r = G.git_branch(name="new", old="old", action="rename", cwd=repo)
    assert r["success"] is True
    branches = G.git_branch(cwd=repo)["branches"]
    assert "new" in branches and "old" not in branches


# --- checkout ---

def test_checkout_create_branch(repo):
    c = G.git_checkout("topic", create=True, cwd=repo)
    assert c["success"] is True
    assert c["branch"] == "topic"
    assert G.git_branch(cwd=repo)["current"] == "topic"


def test_checkout_existing(repo):
    G.git_branch(name="dev", action="create", cwd=repo)
    c = G.git_checkout("dev", cwd=repo)
    assert c["success"] is True
    assert G.git_branch(cwd=repo)["current"] == "dev"


def test_checkout_dirty_requires_confirm(repo):
    (repo / "file.txt").write_text("dirty\n")
    G.git_branch(name="dev", action="create", cwd=repo)
    refused = G.git_checkout("dev", cwd=repo)
    assert refused["success"] is False
    assert refused["needs_confirm"] is True
    done = G.git_checkout("dev", confirm=True, cwd=repo)
    assert done["success"] is True


def test_detached_head(repo):
    h = _run(repo, "rev-parse", "HEAD").stdout.strip()
    c = G.git_checkout(h, cwd=repo)
    assert c["success"] is True
    assert c["detached_head"] is True
    st = G.git_status(repo)
    assert st["detached_head"] is True


# --- restore ---

def test_restore_preview(repo):
    (repo / "file.txt").write_text("changed content\n")
    r = G.git_restore(paths=["file.txt"], preview=True, cwd=repo)
    assert r["success"] is True
    # Content must be unchanged after preview
    assert (repo / "file.txt").read_text() == "changed content\n"


def test_restore_requires_confirm(repo):
    (repo / "file.txt").write_text("changed content\n")
    refused = G.git_restore(paths=["file.txt"], working_tree=True, cwd=repo)
    assert refused["success"] is False
    assert refused["needs_confirm"] is True


def test_restore_working_tree(repo):
    (repo / "file.txt").write_text("changed content\n")
    r = G.git_restore(paths=["file.txt"], confirm=True, cwd=repo)
    assert r["success"] is True
    assert (repo / "file.txt").read_text() == "hello\n"


def test_restore_staged(repo):
    # Stage a modification to an already-tracked file.
    (repo / "file.txt").write_text("staged now\n")
    G.git_add(paths=["file.txt"], cwd=repo)
    assert "file.txt" in G.git_status(repo)["staged"]
    r = G.git_restore(paths=["file.txt"], staged=True, confirm=True, cwd=repo)
    assert r["success"] is True
    assert "file.txt" not in G.git_status(repo)["staged"]


# --- reset ---

def test_reset_soft(repo):
    (repo / "a.txt").write_text("a\n")
    G.git_add(paths=["a.txt"], cwd=repo)
    # a.txt is staged; reset --soft keeps it staged
    r = G.git_reset(mode="soft", confirm=True, cwd=repo)
    assert r["success"] is True
    assert "a.txt" in G.git_status(repo)["staged"]


def test_reset_mixed(repo):
    (repo / "a.txt").write_text("a\n")
    G.git_add(paths=["a.txt"], cwd=repo)
    r = G.git_reset(mode="mixed", confirm=True, cwd=repo)
    assert r["success"] is True
    # mixed: changes stay in working tree but unstaged
    s = G.git_status(repo)
    assert "a.txt" in s["untracked"]
    assert "a.txt" not in s["staged"]


def test_reset_requires_confirm(repo):
    r = G.git_reset(mode="mixed", cwd=repo)
    assert r["success"] is False
    assert r["needs_confirm"] is True


def test_reset_hard_rejected(repo):
    r = G.git_reset(mode="hard", confirm=True, cwd=repo)
    assert r["success"] is False
    assert "soft and --mixed" in r["reason"]


# --- clone ---

def test_clone(repo, tmp_path):
    dest = tmp_path / "clone_dest"
    # Make a bare-ish source the test repo itself; clone it locally.
    r = G.git_clone(str(repo), target_dir=str(dest), cwd=tmp_path)
    assert r["success"] is True
    assert (dest / "file.txt").exists()


def test_clone_invalid_url(tmp_path):
    r = G.git_clone("not-a-real-url://nope/nope", target_dir="x", cwd=tmp_path)
    assert r["success"] is False
    assert r["reason"]
