"""CLI tool to view regression hotspots."""

from core.backlog import EngineeringBacklog
from core.insights import EngineeringInsights


def show_hotspots():
    """Display regression hotspots from the backlog."""
    backlog = EngineeringBacklog()
    insights = EngineeringInsights(backlog)

    print("=" * 60)
    print("REGRESSION HOTSPOTS")
    print("=" * 60)
    print()

    hotspots = insights.regression_hotspots()
    if not hotspots:
        print("No regression hotspots identified.")
        return

    print(f"Found {len(hotspots)} issues requiring regression tests:\n")

    for i, task in enumerate(hotspots, 1):
        print(f"{i}. {task.title}")
        print(f"   Category: {task.category}")
        print(f"   Occurrences: {task.occurrences}")
        print(f"   Confidence: {task.confidence*100:.0f}%")
        print(f"   Priority: {task.priority}")
        print(f"   Root cause: {task.root_cause}")
        print(f"   Recommendation: {task.recommended_fix}")
        print()


if __name__ == "__main__":
    show_hotspots()
