"""Engineering Backlog - persistent storage for identified improvements."""

import json
import os
import time
from dataclasses import dataclass, asdict
from typing import List, Optional
from core.reflection import EngineeringIssue


@dataclass
class EngineeringTask:
    """A persisted engineering improvement task with diagnostic data."""
    id: str
    title: str  # Human-readable title
    layer: str
    category: str  # IssueCategory enum value
    reason: str
    impact: str
    suggested_fix: str
    evidence: list  # List of evidence strings
    regression_required: bool
    status: str  # open, in_progress, resolved
    priority: int  # Computed from multiple factors
    occurrences: int  # How many times this issue was seen
    confidence: float  # 0.0 to 1.0
    root_cause: Optional[str]  # Likely root cause
    alternatives: list  # Alternative explanations
    recommended_fix: str  # Detailed recommendation
    first_seen: float  # Unix timestamp
    last_seen: float  # Unix timestamp
    resolved_at: Optional[float] = None


class EngineeringBacklog:
    """Manages persistent engineering task backlog."""

    def __init__(self, backlog_path: str = ".friday_backlog.json"):
        self.backlog_path = backlog_path
        self.tasks: List[EngineeringTask] = []
        self._load()

    def _load(self):
        """Load backlog from disk."""
        if not os.path.exists(self.backlog_path):
            self.tasks = []
            return

        try:
            with open(self.backlog_path, 'r') as f:
                data = json.load(f)
                self.tasks = [EngineeringTask(**t) for t in data.get('tasks', [])]
        except Exception as e:
            print(f"[backlog] failed to load: {e}")
            self.tasks = []

    def _save(self):
        """Persist backlog to disk."""
        try:
            data = {
                'version': '1.0',
                'tasks': [asdict(t) for t in self.tasks]
            }
            with open(self.backlog_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[backlog] failed to save: {e}")

    def _generate_id_from_category(self, category: str, reason: str) -> str:
        """Generate stable ID from category and reason."""
        key = f"{category}:{reason[:50]}"
        return key.lower().replace(' ', '_').replace(':', '_')

    def _generate_title(self, reason: str) -> str:
        """Generate human-readable title from reason."""
        # Capitalize first letter, truncate at 80 chars
        title = reason[0].upper() + reason[1:] if reason else "Unknown issue"
        return title[:80]

    def record_issue(self, issue: EngineeringIssue, root_cause=None) -> EngineeringTask:
        """Record an engineering issue with diagnostic data, merging with existing if duplicate."""
        from core.diagnostics import IssueClassifier, RootCauseAnalyzer
        from core.priority import PriorityEngine

        # Classify and diagnose the issue
        classifier = IssueClassifier()
        category = classifier.classify(issue.layer, issue.reason, issue.evidence)

        analyzer = RootCauseAnalyzer()
        diagnosis = analyzer.analyze(
            category=category,
            layer=issue.layer,
            reason=issue.reason,
            evidence=issue.evidence,
            impact=issue.impact
        )

        # Generate stable ID from category and reason
        issue_id = self._generate_id_from_category(category.value, issue.reason)
        now = time.time()

        # Check for existing task
        existing = None
        for task in self.tasks:
            if task.id == issue_id and task.status == "open":
                existing = task
                break

        if existing:
            # Increment occurrences and update priority
            existing.occurrences += 1
            existing.last_seen = now

            # Append new evidence if different
            if issue.evidence not in existing.evidence:
                existing.evidence.append(issue.evidence)

            # Recalculate priority with updated occurrences
            priority_engine = PriorityEngine()
            existing.priority = priority_engine.calculate_priority(
                impact=existing.impact,
                occurrences=existing.occurrences,
                confidence=existing.confidence,
                category=category,
                regression_required=existing.regression_required
            )

            self._save()
            return existing

        # Create new task with diagnostic data
        priority_engine = PriorityEngine()
        priority = priority_engine.calculate_priority(
            impact=issue.impact,
            occurrences=1,
            confidence=diagnosis.confidence,
            category=category,
            regression_required=diagnosis.regression_required
        )

        task = EngineeringTask(
            id=issue_id,
            title=self._generate_title(issue.reason),
            layer=issue.layer,
            category=category.value,
            reason=issue.reason,
            impact=issue.impact,
            suggested_fix=issue.suggested_fix,
            evidence=[issue.evidence],
            regression_required=diagnosis.regression_required,
            status="open",
            priority=priority,
            occurrences=1,
            confidence=diagnosis.confidence,
            root_cause=diagnosis.likely_cause,
            alternatives=diagnosis.alternatives,
            recommended_fix=diagnosis.recommended_fix,
            first_seen=now,
            last_seen=now
        )
        self.tasks.append(task)
        self._save()
        return task

    def get_open_tasks(self) -> List[EngineeringTask]:
        """Get all open tasks sorted by priority (highest first)."""
        open_tasks = [t for t in self.tasks if t.status == "open"]
        return sorted(open_tasks, key=lambda t: t.priority, reverse=True)

    def get_task(self, task_id: str) -> Optional[EngineeringTask]:
        """Get a specific task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def resolve_task(self, task_id: str):
        """Mark a task as resolved."""
        task = self.get_task(task_id)
        if task:
            task.status = "resolved"
            task.resolved_at = time.time()
            self._save()

    def get_summary(self) -> str:
        """Get a summary of the backlog state."""
        open_tasks = self.get_open_tasks()
        if not open_tasks:
            return "Engineering backlog is empty."

        high = [t for t in open_tasks if t.impact == "HIGH"]
        medium = [t for t in open_tasks if t.impact == "MEDIUM"]
        low = [t for t in open_tasks if t.impact == "LOW"]

        summary = f"Engineering Backlog: {len(open_tasks)} open tasks\n"
        summary += f"  HIGH: {len(high)}, MEDIUM: {len(medium)}, LOW: {len(low)}\n\n"
        summary += "Top 3 by priority:\n"
        for i, task in enumerate(open_tasks[:3], 1):
            conf = f"{task.confidence*100:.0f}%" if hasattr(task, 'confidence') else "N/A"
            summary += f"{i}. [{task.impact}] {task.title} (confidence: {conf}, occurrences: {task.occurrences})\n"
            if hasattr(task, 'root_cause') and task.root_cause:
                summary += f"   → {task.root_cause}\n"

        return summary
