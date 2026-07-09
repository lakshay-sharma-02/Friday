"""Engineering Insights - query and analyze the backlog."""

from typing import List, Dict
from core.backlog import EngineeringBacklog, EngineeringTask


class EngineeringInsights:
    """Generate insights from engineering backlog data."""

    def __init__(self, backlog: EngineeringBacklog):
        self.backlog = backlog

    def what_keeps_failing(self) -> List[EngineeringTask]:
        """Get most frequently occurring issues."""
        open_tasks = self.backlog.get_open_tasks()
        # Sort by occurrences descending
        return sorted(open_tasks, key=lambda t: t.occurrences, reverse=True)[:5]

    def biggest_engineering_problem(self) -> EngineeringTask:
        """Get highest priority issue."""
        open_tasks = self.backlog.get_open_tasks()
        if not open_tasks:
            return None
        # Already sorted by priority descending
        return open_tasks[0]

    def what_to_fix_next(self) -> EngineeringTask:
        """Get next recommended fix (highest priority)."""
        return self.biggest_engineering_problem()

    def performance_bottlenecks(self) -> List[EngineeringTask]:
        """Get all performance-related issues."""
        open_tasks = self.backlog.get_open_tasks()
        perf_tasks = [t for t in open_tasks if t.category == "Performance"]
        return sorted(perf_tasks, key=lambda t: t.priority, reverse=True)

    def regression_hotspots(self) -> List[EngineeringTask]:
        """Get issues that occur most often and need regression tests."""
        open_tasks = self.backlog.get_open_tasks()
        regression_tasks = [t for t in open_tasks if t.regression_required]
        return sorted(regression_tasks, key=lambda t: t.occurrences, reverse=True)[:5]

    def architectural_weaknesses(self) -> List[EngineeringTask]:
        """Get architecture-related issues."""
        open_tasks = self.backlog.get_open_tasks()
        arch_tasks = [t for t in open_tasks if t.category == "Architecture"]
        return sorted(arch_tasks, key=lambda t: t.priority, reverse=True)

    def category_breakdown(self) -> Dict[str, int]:
        """Get count of issues by category."""
        open_tasks = self.backlog.get_open_tasks()
        breakdown = {}
        for task in open_tasks:
            category = task.category
            breakdown[category] = breakdown.get(category, 0) + 1
        return dict(sorted(breakdown.items(), key=lambda x: x[1], reverse=True))

    def confidence_analysis(self) -> Dict[str, List[EngineeringTask]]:
        """Group issues by confidence level."""
        open_tasks = self.backlog.get_open_tasks()
        high_conf = [t for t in open_tasks if t.confidence >= 0.8]
        medium_conf = [t for t in open_tasks if 0.5 <= t.confidence < 0.8]
        low_conf = [t for t in open_tasks if t.confidence < 0.5]

        return {
            "high": sorted(high_conf, key=lambda t: t.priority, reverse=True),
            "medium": sorted(medium_conf, key=lambda t: t.priority, reverse=True),
            "low": sorted(low_conf, key=lambda t: t.priority, reverse=True)
        }

    def get_statistics(self) -> Dict:
        """Get backlog statistics."""
        open_tasks = self.backlog.get_open_tasks()
        resolved_tasks = [t for t in self.backlog.tasks if t.status == "resolved"]

        total_occurrences = sum(t.occurrences for t in open_tasks)
        avg_confidence = sum(t.confidence for t in open_tasks) / len(open_tasks) if open_tasks else 0

        return {
            "total_open": len(open_tasks),
            "total_resolved": len(resolved_tasks),
            "total_occurrences": total_occurrences,
            "avg_confidence": avg_confidence,
            "high_priority": len([t for t in open_tasks if t.priority > 200]),
            "needs_regression": len([t for t in open_tasks if t.regression_required]),
            "categories": self.category_breakdown()
        }
