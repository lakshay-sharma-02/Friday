"""Deterministic tests for Phase 6D plan validation, repair, risk, and guards."""

import pytest

from core.plan_validation import (
    validate_and_prepare_plan,
    validate_step,
    tool_risk,
)


# --- valid plans ---

def test_valid_plan_accepted():
    plan = [
        {"tool": "git_status", "args": {}, "description": "status"},
        {"tool": "read_file", "args": {"path": "x.txt"}, "description": "read"},
    ]
    r = validate_and_prepare_plan(plan)
    assert r["accepted"] is True
    assert len(r["steps"]) == 2
    assert r["risk_level"] == "LOW"


def test_valid_plan_risk_propagates_to_high():
    plan = [
        {"tool": "read_file", "args": {"path": "x"}},
        {"tool": "shell", "args": {"command": "ls"}},
    ]
    r = validate_and_prepare_plan(plan)
    assert r["accepted"] is True
    assert r["risk_level"] == "HIGH"
    assert r["steps"][1]["risk_level"] == "HIGH"


# --- invalid JSON / structure ---

def test_non_array_plan_rejected():
    r = validate_and_prepare_plan({"tool": "git_status"})
    assert r["accepted"] is False
    assert "JSON array" in r["message"]


def test_empty_plan_rejected():
    r = validate_and_prepare_plan([])
    assert r["accepted"] is False


def test_malformed_step_not_dict():
    r = validate_and_prepare_plan(["not-a-dict"])
    assert r["accepted"] is False
    assert r["errors"]


# --- unknown tools ---

def test_unknown_tool_rejected():
    plan = [{"tool": "frobnicate", "args": {}}]
    r = validate_and_prepare_plan(plan)
    assert r["accepted"] is False
    assert any("unknown tool" in e["error"] for e in r["errors"])


# --- missing / wrong-type args ---

def test_missing_required_arg_rejected():
    # read_file requires 'path'
    plan = [{"tool": "read_file", "args": {}}]
    r = validate_and_prepare_plan(plan)
    assert r["accepted"] is False
    assert any("missing required argument" in e["error"] for e in r["errors"])


def test_wrong_arg_type_rejected():
    # read_file 'path' must be a string
    plan = [{"tool": "read_file", "args": {"path": 123}}]
    r = validate_and_prepare_plan(plan)
    assert r["accepted"] is False
    assert any("expected string" in e["error"] for e in r["errors"])


# --- duplicate / unknown fields ---

def test_unknown_field_dropped_repairable():
    plan = [{"tool": "git_status", "args": {}, "bogus": "x", "description": "d"}]
    r = validate_and_prepare_plan(plan)
    assert r["accepted"] is True
    step = r["steps"][0]
    assert "bogus" not in step
    assert r["repairs"]


def test_unknown_arg_dropped_repairable():
    plan = [{"tool": "git_status", "args": {"phantom": 1}}]
    r = validate_and_prepare_plan(plan)
    assert r["accepted"] is True
    assert "phantom" not in r["steps"][0]["args"]


# --- repairable: tool name casing ---

def test_tool_name_casing_repaired():
    plan = [{"tool": "Git_Status", "args": {}}]
    r = validate_and_prepare_plan(plan)
    assert r["accepted"] is True
    assert r["steps"][0]["tool"] == "git_status"
    assert r["repairs"]


# --- repairable: missing optional args object ---

def test_missing_args_object_repaired():
    plan = [{"tool": "git_status"}]
    r = validate_and_prepare_plan(plan)
    assert r["accepted"] is True
    assert r["steps"][0]["args"] == {}
    assert r["repairs"]


# --- non-repairable: missing required + unknown tool mixed rejected ---

def test_mixed_fatal_rejected():
    plan = [
        {"tool": "git_status", "args": {}},          # ok
        {"tool": "read_file", "args": {}},           # missing required path
    ]
    r = validate_and_prepare_plan(plan)
    assert r["accepted"] is False
    assert any("missing required argument" in e["error"] for e in r["errors"])


# --- risk classification ---

def test_risk_classification():
    assert tool_risk("read_file") == "LOW"
    assert tool_risk("list_directory") == "LOW"
    assert tool_risk("git_status") == "LOW"
    assert tool_risk("write_file") == "MEDIUM"
    assert tool_risk("git_commit") == "MEDIUM"
    assert tool_risk("shell") == "HIGH"
    assert tool_risk("git_reset") == "HIGH"
    assert tool_risk("process") == "HIGH"


def test_risk_unmapped_defaults_medium():
    # An unmapped-but-registered tool should not silently be LOW.
    assert tool_risk("start_shell") == "HIGH"
    assert tool_risk("git_branch") == "MEDIUM"


# --- step-level strict validation ---

def test_validate_step_strict():
    assert validate_step({"tool": "git_status", "args": {}}, 0)[0] is True
    ok, err = validate_step({"tool": "nope", "args": {}}, 0)
    assert ok is False
    assert "unknown tool" in err


# --- never raises ---

def test_validate_never_raises_on_garbage():
    for bad in [None, "string", 42, {}, [1, 2, 3], [{"tool": None}]]:
        try:
            validate_and_prepare_plan(bad)
        except Exception as e:
            pytest.fail(f"validate_and_prepare_plan raised on {bad!r}: {e}")

# --- execution guards ---

def test_execution_guards():
    from core.plan_validation import verify_execution_guards
    from core.world import WorldState, WorkspaceState
    from core.world import ComputerState
    from core.world import NetworkState
    from core.world import ProcessState
    from core.world import RuntimeState
    
    class MockIntent:
        def __init__(self):
            self.id = "test"
            self.payload = {"text": "test"}
            self.permission_ceiling = 0
            self.source = "test"
            
    world = WorldState(
        workspace=WorkspaceState(cwd="/does/not/exist", is_git_repo=False),
        computer=ComputerState(),
        network=NetworkState(internet_reachable=True),
        processes=ProcessState(),
        runtime=RuntimeState(task_text="test"), developer=None, observed_at=0.0
    )
    intent = MockIntent()
    
    # 1. invalid tool / args
    ok, err = verify_execution_guards({"tool": "read_file"}, intent, world)
    assert not ok
    assert "missing required argument" in err
    
    # 2. workspace missing
    ok, err = verify_execution_guards({"tool": "read_file", "args": {"path": "x", "cwd": "/does/not/exist"}}, intent, world)
    assert not ok
    assert "Workspace" in err
    
    # 3. prerequisites (git)
    # Give it a valid cwd so it doesn't fail on workspace missing
    world.workspace.cwd = "/"
    ok, err = verify_execution_guards({"tool": "git_status", "args": {"cwd": "/"}}, intent, world)
    assert not ok
    assert "requires a git repository" in err
    
    # 4. success (with git repo)
    world.workspace.is_git_repo = True
    ok, err = verify_execution_guards({"tool": "git_status", "args": {"cwd": "/"}}, intent, world)
    assert ok, err

