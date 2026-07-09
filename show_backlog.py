"""CLI command to view engineering backlog."""

from core.backlog import EngineeringBacklog


def show_backlog():
    """Display the current engineering backlog."""
    backlog = EngineeringBacklog()
    print(backlog.get_summary())
    print()

    open_tasks = backlog.get_open_tasks()
    if open_tasks:
        print("Detailed view:\n")
        for task in open_tasks[:5]:  # Show top 5
            print(f"ID: {task.id}")
            print(f"Title: {task.title}")
            print(f"Layer: {task.layer}")

            # Phase 13: Enhanced diagnostic data
            if hasattr(task, 'category'):
                print(f"Category: {task.category}")
            if hasattr(task, 'confidence'):
                print(f"Confidence: {task.confidence*100:.0f}%")

            print(f"Impact: {task.impact}")
            print(f"Priority: {task.priority}")
            print(f"Reason: {task.reason}")

            # Phase 13: Root cause analysis
            if hasattr(task, 'root_cause') and task.root_cause:
                print(f"Root cause: {task.root_cause}")
            if hasattr(task, 'recommended_fix') and task.recommended_fix:
                print(f"Recommended fix: {task.recommended_fix}")
            else:
                print(f"Suggested fix: {task.suggested_fix}")

            # Evidence
            if hasattr(task, 'evidence') and isinstance(task.evidence, list):
                print(f"Evidence: {', '.join(task.evidence[:2])}")  # Show first 2
            else:
                print(f"Evidence: {task.evidence if hasattr(task, 'evidence') else 'N/A'}")

            print(f"Occurrences: {task.occurrences}")
            print(f"Regression required: {task.regression_required}")
            print()


if __name__ == "__main__":
    show_backlog()
