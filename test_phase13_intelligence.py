"""Test Phase 13: Engineering Intelligence - diagnostics and insights."""

import pytest
import os
from core.diagnostics import IssueClassifier, RootCauseAnalyzer, IssueCategory
from core.priority import PriorityEngine
from core.backlog import EngineeringBacklog, EngineeringTask
from core.insights import EngineeringInsights
from core.reflection import EngineeringIssue


@pytest.fixture
def clean_backlog():
    """Ensure clean backlog for testing."""
    backlog_path = ".friday_backlog_test_phase13.json"
    if os.path.exists(backlog_path):
        os.remove(backlog_path)
    yield backlog_path
    if os.path.exists(backlog_path):
        os.remove(backlog_path)


def test_issue_classifier_memory():
    """Classifier correctly identifies memory issues."""
    classifier = IssueClassifier()

    category = classifier.classify("Memory", "Memory search slow", "Search took 1.5s")
    assert category == IssueCategory.MEMORY


def test_issue_classifier_planner_performance():
    """Classifier identifies planner performance issues."""
    classifier = IssueClassifier()

    category = classifier.classify("Planner", "Planning took longer than 15s", "Took 16s")
    assert category == IssueCategory.PERFORMANCE


def test_issue_classifier_executor_failure():
    """Classifier identifies executor failures."""
    classifier = IssueClassifier()

    category = classifier.classify("Executor", "Task failed after 3 attempts", "Tool: shell, exit code: 1")
    assert category == IssueCategory.TOOL


def test_root_cause_memory_slow_search():
    """Root cause analyzer diagnoses slow memory search."""
    analyzer = RootCauseAnalyzer()

    result = analyzer.analyze(
        category=IssueCategory.MEMORY,
        layer="Memory",
        reason="Memory search exceeded 1s threshold",
        evidence="Search took 1.5s",
        impact="MEDIUM"
    )

    assert result.category == IssueCategory.MEMORY
    assert result.confidence >= 0.8
    assert "inefficient" in result.likely_cause.lower()
    assert len(result.supporting_evidence) > 0
    assert len(result.alternatives) > 0


def test_root_cause_planner_retry():
    """Root cause analyzer diagnoses planner retry."""
    analyzer = RootCauseAnalyzer()

    result = analyzer.analyze(
        category=IssueCategory.PLANNER,
        layer="Planner",
        reason="Required retry to complete task",
        evidence="Retry count: 2",
        impact="MEDIUM"
    )

    assert result.category == IssueCategory.PLANNER
    assert result.confidence >= 0.7
    assert "plan quality" in result.likely_cause.lower()
    assert result.regression_required is True


def test_root_cause_executor_failure():
    """Root cause analyzer diagnoses executor failure."""
    analyzer = RootCauseAnalyzer()

    result = analyzer.analyze(
        category=IssueCategory.EXECUTOR,
        layer="Executor",
        reason="Task failed after 3 attempts",
        evidence="Tool: shell, Error: command not found",
        impact="HIGH"
    )

    assert result.category == IssueCategory.EXECUTOR
    assert result.confidence >= 0.85
    assert "execution failure" in result.likely_cause.lower()
    assert result.regression_required is True


def test_priority_engine_high_impact():
    """Priority engine scores high impact issues correctly."""
    engine = PriorityEngine()

    priority = engine.calculate_priority(
        impact="HIGH",
        occurrences=1,
        confidence=0.9,
        category=IssueCategory.EXECUTOR,
        regression_required=True
    )

    # HIGH (100) + frequency (10) + confidence (45) + category (25) + regression (20) = 200
    assert priority >= 190


def test_priority_engine_frequency_bonus():
    """Priority increases with frequency."""
    engine = PriorityEngine()

    priority1 = engine.calculate_priority(
        impact="MEDIUM",
        occurrences=1,
        confidence=0.8,
        category=IssueCategory.MEMORY,
        regression_required=False
    )

    priority2 = engine.calculate_priority(
        impact="MEDIUM",
        occurrences=5,
        confidence=0.8,
        category=IssueCategory.MEMORY,
        regression_required=False
    )

    assert priority2 > priority1


def test_priority_engine_escalation():
    """Priority engine identifies issues needing escalation."""
    engine = PriorityEngine()

    # High priority should escalate
    assert engine.should_escalate(priority=350, occurrences=5) is True

    # High frequency should escalate
    assert engine.should_escalate(priority=200, occurrences=25) is True

    # Normal cases should not escalate
    assert engine.should_escalate(priority=150, occurrences=3) is False


def test_backlog_records_with_diagnostics(clean_backlog):
    """Backlog records issues with full diagnostic data."""
    backlog = EngineeringBacklog(clean_backlog)

    issue = EngineeringIssue(
        layer="Memory",
        reason="Memory search exceeded 1s threshold",
        impact="MEDIUM",
        suggested_fix="Add caching",
        evidence="Search took 1.5s",
        regression_required=False
    )

    task = backlog.record_issue(issue)

    assert task.category == "Memory"
    assert task.confidence > 0
    assert task.root_cause is not None
    assert len(task.alternatives) > 0
    assert task.recommended_fix is not None
    assert isinstance(task.evidence, list)


def test_insights_biggest_problem(clean_backlog):
    """Engineering insights identifies biggest problem."""
    backlog = EngineeringBacklog(clean_backlog)

    # Add multiple issues
    backlog.record_issue(EngineeringIssue(
        layer="Memory",
        reason="Memory search slow",
        impact="MEDIUM",
        suggested_fix="Cache",
        evidence="1.5s",
        regression_required=False
    ))

    backlog.record_issue(EngineeringIssue(
        layer="Executor",
        reason="Task failed after retries",
        impact="HIGH",
        suggested_fix="Fix",
        evidence="Error",
        regression_required=True
    ))

    insights = EngineeringInsights(backlog)
    biggest = insights.biggest_engineering_problem()

    assert biggest is not None
    assert biggest.impact == "HIGH"


def test_insights_frequent_failures(clean_backlog):
    """Engineering insights identifies most frequent failures."""
    backlog = EngineeringBacklog(clean_backlog)

    issue = EngineeringIssue(
        layer="Memory",
        reason="Memory search slow",
        impact="MEDIUM",
        suggested_fix="Cache",
        evidence="1.5s",
        regression_required=False
    )

    # Record same issue multiple times
    for _ in range(5):
        backlog.record_issue(issue)

    insights = EngineeringInsights(backlog)
    failing = insights.what_keeps_failing()

    assert len(failing) > 0
    assert failing[0].occurrences == 5


def test_insights_performance_bottlenecks(clean_backlog):
    """Engineering insights identifies performance issues."""
    backlog = EngineeringBacklog(clean_backlog)

    backlog.record_issue(EngineeringIssue(
        layer="Planner",
        reason="Planning took longer than 15s",
        impact="MEDIUM",
        suggested_fix="Optimize",
        evidence="Took 16s",
        regression_required=False
    ))

    insights = EngineeringInsights(backlog)
    perf = insights.performance_bottlenecks()

    assert len(perf) > 0
    assert perf[0].category == "Performance"


def test_insights_regression_hotspots(clean_backlog):
    """Engineering insights identifies regression hotspots."""
    backlog = EngineeringBacklog(clean_backlog)

    issue = EngineeringIssue(
        layer="Executor",
        reason="Task failed",
        impact="HIGH",
        suggested_fix="Fix",
        evidence="Error",
        regression_required=True
    )

    for _ in range(3):
        backlog.record_issue(issue)

    insights = EngineeringInsights(backlog)
    hotspots = insights.regression_hotspots()

    assert len(hotspots) > 0
    assert hotspots[0].regression_required is True
    assert hotspots[0].occurrences == 3


def test_insights_category_breakdown(clean_backlog):
    """Engineering insights provides category breakdown."""
    backlog = EngineeringBacklog(clean_backlog)

    backlog.record_issue(EngineeringIssue(
        layer="Memory",
        reason="Memory issue 1",
        impact="MEDIUM",
        suggested_fix="Fix",
        evidence="E1",
        regression_required=False
    ))

    backlog.record_issue(EngineeringIssue(
        layer="Memory",
        reason="Memory issue 2",
        impact="MEDIUM",
        suggested_fix="Fix",
        evidence="E2",
        regression_required=False
    ))

    backlog.record_issue(EngineeringIssue(
        layer="Planner",
        reason="Planning slow",
        impact="MEDIUM",
        suggested_fix="Fix",
        evidence="E3",
        regression_required=False
    ))

    insights = EngineeringInsights(backlog)
    breakdown = insights.category_breakdown()

    assert "Memory" in breakdown
    assert breakdown["Memory"] == 2


def test_insights_statistics(clean_backlog):
    """Engineering insights provides comprehensive statistics."""
    backlog = EngineeringBacklog(clean_backlog)

    issue = EngineeringIssue(
        layer="Memory",
        reason="Memory search slow",
        impact="MEDIUM",
        suggested_fix="Cache",
        evidence="1.5s",
        regression_required=False
    )

    for _ in range(3):
        backlog.record_issue(issue)

    insights = EngineeringInsights(backlog)
    stats = insights.get_statistics()

    assert stats["total_open"] == 1
    assert stats["total_occurrences"] == 3
    assert stats["avg_confidence"] > 0
    assert "categories" in stats
