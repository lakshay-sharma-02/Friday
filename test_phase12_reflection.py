"""Test Phase 12: Engineering Reflection & Self-Improvement."""

import pytest
import os
import json
from core.reflection import EngineeringReflection, EngineeringIssue
from core.backlog import EngineeringBacklog, EngineeringTask
from core.run import PipelineRun
from core.intent import Intent
from core.world import WorldState, WorkspaceState, ComputerState, NetworkState, ProcessState


@pytest.fixture
def clean_backlog():
    """Ensure clean backlog for testing."""
    backlog_path = ".friday_backlog_test.json"
    if os.path.exists(backlog_path):
        os.remove(backlog_path)
    yield backlog_path
    if os.path.exists(backlog_path):
        os.remove(backlog_path)


def test_reflection_no_issue_on_success():
    """Reflection returns None when execution is clean."""
    reflection = EngineeringReflection()

    intent = Intent(kind="task", payload={"text": "test task"}, response_future=None)
    run = PipelineRun(intent=intent, status="completed", plan=[{"tool": "read_file", "args": {}}])
    run.execution_log = [{"tool": "read_file", "success": True, "output": "content"}]

    world = WorldState.empty(cwd=".")

    timings = {
        "observe": 0.1,
        "health": 0.05,
        "memory_search": 0.2,
        "plan": 5.0,
        "execute": 1.0
    }

    issue = reflection.reflect(run, world, timings)
    assert issue is None


def test_reflection_detects_failure():
    """Reflection identifies issues when task fails with retries."""
    reflection = EngineeringReflection()

    intent = Intent(kind="task", payload={"text": "test task"}, response_future=None)
    run = PipelineRun(intent=intent, status="failed", retry_count=2)
    run.execution_log = [
        {"tool": "shell", "success": False, "output": "command not found", "exit_code": 127}
    ]

    world = WorldState.empty(cwd=".")

    timings = {"observe": 0.1, "plan": 5.0}

    issue = reflection.reflect(run, world, timings)
    assert issue is not None
    assert issue.layer == "Executor"
    assert issue.impact == "HIGH"
    assert "failed after" in issue.reason
    assert issue.regression_required is True


def test_reflection_detects_slow_memory():
    """Reflection identifies slow memory searches."""
    reflection = EngineeringReflection()

    intent = Intent(kind="task", payload={"text": "test task"}, response_future=None)
    run = PipelineRun(intent=intent, status="completed")

    world = WorldState.empty(cwd=".")

    timings = {
        "observe": 0.1,
        "memory_search": 1.5,  # Exceeds 1s threshold
        "plan": 5.0
    }

    issue = reflection.reflect(run, world, timings)
    assert issue is not None
    assert issue.layer == "Memory"
    assert "exceeded 1s" in issue.reason
    assert issue.impact == "MEDIUM"


def test_reflection_detects_slow_planning():
    """Reflection identifies slow planning."""
    reflection = EngineeringReflection()

    intent = Intent(kind="task", payload={"text": "test task"}, response_future=None)
    run = PipelineRun(intent=intent, status="completed")

    world = WorldState.empty(cwd=".")

    timings = {
        "observe": 0.1,
        "plan": 16.0,  # Exceeds 15s threshold
    }

    issue = reflection.reflect(run, world, timings)
    assert issue is not None
    assert issue.layer == "Planner"
    assert "longer than 15s" in issue.reason


def test_backlog_records_new_issue(clean_backlog):
    """Backlog creates new task for first occurrence."""
    backlog = EngineeringBacklog(clean_backlog)

    issue = EngineeringIssue(
        layer="Memory",
        reason="Memory search slow",
        impact="MEDIUM",
        suggested_fix="Add caching",
        evidence="Search took 1.5s",
        regression_required=False
    )

    task = backlog.record_issue(issue)
    assert task.id is not None
    assert task.layer == "Memory"
    assert task.occurrences == 1
    assert task.status == "open"
    # Phase 13: Priority now includes confidence + category weight
    # MEDIUM (50) + frequency (10) + confidence (~30) + category (15) = ~105
    assert task.priority > 60  # Increased due to Phase 13 multi-factor calculation


def test_backlog_merges_duplicate_issues(clean_backlog):
    """Backlog increments occurrences for duplicate issues."""
    backlog = EngineeringBacklog(clean_backlog)

    issue = EngineeringIssue(
        layer="Memory",
        reason="Memory search slow",
        impact="MEDIUM",
        suggested_fix="Add caching",
        evidence="Search took 1.5s",
        regression_required=False
    )

    task1 = backlog.record_issue(issue)
    initial_priority = task1.priority
    task2 = backlog.record_issue(issue)

    assert task1.id == task2.id
    assert task2.occurrences == 2
    assert task2.priority > initial_priority  # Priority increased


def test_backlog_prioritizes_by_impact_and_frequency(clean_backlog):
    """Backlog prioritizes HIGH impact and frequent issues."""
    backlog = EngineeringBacklog(clean_backlog)

    high_issue = EngineeringIssue(
        layer="Executor",
        reason="Task failed",
        impact="HIGH",
        suggested_fix="Fix",
        evidence="Error",
        regression_required=True
    )

    low_issue = EngineeringIssue(
        layer="Observers",
        reason="Observation slow",
        impact="LOW",
        suggested_fix="Optimize",
        evidence="Took 2.5s",
        regression_required=False
    )

    backlog.record_issue(low_issue)
    backlog.record_issue(low_issue)
    backlog.record_issue(low_issue)  # Low issue seen 3 times
    backlog.record_issue(high_issue)  # High issue seen once

    open_tasks = backlog.get_open_tasks()
    # HIGH impact task should be first even with fewer occurrences
    assert open_tasks[0].impact == "HIGH"


def test_backlog_persistence(clean_backlog):
    """Backlog persists and loads from disk."""
    backlog1 = EngineeringBacklog(clean_backlog)

    issue = EngineeringIssue(
        layer="Memory",
        reason="Memory search slow",
        impact="MEDIUM",
        suggested_fix="Add caching",
        evidence="Search took 1.5s",
        regression_required=False
    )

    task1 = backlog1.record_issue(issue)

    # Create new backlog instance (simulates new session)
    backlog2 = EngineeringBacklog(clean_backlog)
    task2 = backlog2.get_task(task1.id)

    assert task2 is not None
    assert task2.layer == task1.layer
    assert task2.reason == task1.reason


def test_backlog_resolve_task(clean_backlog):
    """Backlog can resolve tasks."""
    backlog = EngineeringBacklog(clean_backlog)

    issue = EngineeringIssue(
        layer="Memory",
        reason="Memory search slow",
        impact="MEDIUM",
        suggested_fix="Add caching",
        evidence="Search took 1.5s",
        regression_required=False
    )

    task = backlog.record_issue(issue)
    assert task.status == "open"

    backlog.resolve_task(task.id)

    resolved_task = backlog.get_task(task.id)
    assert resolved_task.status == "resolved"
    assert resolved_task.resolved_at is not None

    # Resolved tasks not in open list
    open_tasks = backlog.get_open_tasks()
    assert task.id not in [t.id for t in open_tasks]


def test_backlog_summary_empty(clean_backlog):
    """Backlog summary handles empty state."""
    backlog = EngineeringBacklog(clean_backlog)
    summary = backlog.get_summary()
    assert "empty" in summary.lower()


def test_backlog_summary_with_tasks(clean_backlog):
    """Backlog summary shows task breakdown."""
    backlog = EngineeringBacklog(clean_backlog)

    high_issue = EngineeringIssue(
        layer="Executor",
        reason="Task failed",
        impact="HIGH",
        suggested_fix="Fix",
        evidence="Error",
        regression_required=True
    )

    medium_issue = EngineeringIssue(
        layer="Memory",
        reason="Slow search",
        impact="MEDIUM",
        suggested_fix="Cache",
        evidence="1.5s",
        regression_required=False
    )

    backlog.record_issue(high_issue)
    backlog.record_issue(medium_issue)

    summary = backlog.get_summary()
    assert "2 open tasks" in summary
    assert "HIGH: 1" in summary
    assert "MEDIUM: 1" in summary
