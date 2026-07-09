"""CLI tool to view engineering insights."""

from core.backlog import EngineeringBacklog
from core.insights import EngineeringInsights


def show_insights():
    """Display engineering insights from the backlog."""
    backlog = EngineeringBacklog()
    insights = EngineeringInsights(backlog)

    print("=" * 60)
    print("ENGINEERING INSIGHTS")
    print("=" * 60)
    print()

    # Statistics
    stats = insights.get_statistics()
    print(f"Open issues: {stats['total_open']}")
    print(f"Resolved issues: {stats['total_resolved']}")
    print(f"Total occurrences: {stats['total_occurrences']}")
    print(f"Average confidence: {stats['avg_confidence']*100:.1f}%")
    print(f"High priority issues: {stats['high_priority']}")
    print(f"Needs regression: {stats['needs_regression']}")
    print()

    # Category breakdown
    print("Issues by category:")
    for category, count in stats['categories'].items():
        print(f"  {category}: {count}")
    print()

    # Biggest problem
    biggest = insights.biggest_engineering_problem()
    if biggest:
        print("BIGGEST ENGINEERING PROBLEM:")
        print(f"  {biggest.title}")
        print(f"  Category: {biggest.category}")
        print(f"  Impact: {biggest.impact}")
        print(f"  Priority: {biggest.priority}")
        print(f"  Confidence: {biggest.confidence*100:.0f}%")
        print(f"  Root cause: {biggest.root_cause}")
        print(f"  Recommendation: {biggest.recommended_fix}")
        print()

    # What keeps failing
    failing = insights.what_keeps_failing()
    if failing:
        print("MOST FREQUENT ISSUES:")
        for i, task in enumerate(failing[:3], 1):
            print(f"{i}. {task.title} (x{task.occurrences})")
            print(f"   Confidence: {task.confidence*100:.0f}% | {task.root_cause}")
        print()

    # Performance bottlenecks
    perf = insights.performance_bottlenecks()
    if perf:
        print("PERFORMANCE BOTTLENECKS:")
        for i, task in enumerate(perf[:3], 1):
            print(f"{i}. {task.title} (priority: {task.priority})")
            print(f"   {task.root_cause}")
        print()

    # Architectural weaknesses
    arch = insights.architectural_weaknesses()
    if arch:
        print("ARCHITECTURAL WEAKNESSES:")
        for i, task in enumerate(arch[:3], 1):
            print(f"{i}. {task.title} (priority: {task.priority})")
            print(f"   {task.root_cause}")
        print()


if __name__ == "__main__":
    show_insights()
