"""Deterministic importance tiering based on access patterns."""

from datetime import datetime, timezone, timedelta


def compute_tier(last_accessed_at: datetime, access_count: int) -> str:
    """Compute tier based on last access time and access count.

    Deterministic formula-based tiering (no LLM judgment):
    - HOT: last_accessed_at within 24 hours OR access_count >= 5
    - WARM: last_accessed_at within 14 days
    - COLD: everything else

    Args:
        last_accessed_at: Last time the row was accessed
        access_count: Number of times accessed

    Returns:
        Tier string: "HOT", "WARM", or "COLD"
    """
    now = datetime.now(timezone.utc)

    # HOT: accessed in last 24h or high access count
    if access_count >= 5:
        return "HOT"

    if last_accessed_at:
        time_since_access = now - last_accessed_at
        if time_since_access <= timedelta(hours=24):
            return "HOT"
        elif time_since_access <= timedelta(days=14):
            return "WARM"

    return "COLD"


def retier_all(store: "MemoryStore") -> dict:
    """Recompute and update tier for all rows in both tables.

    Args:
        store: MemoryStore instance

    Returns:
        Dict with counts of rows moved per tier
    """
    import sys

    try:
        moved = {"HOT": 0, "WARM": 0, "COLD": 0}

        # Retier runs
        runs = store.get_all_runs()
        for run in runs:
            last_accessed = None
            if run.get("last_accessed_at"):
                last_accessed = datetime.fromisoformat(run["last_accessed_at"])

            old_tier = run.get("tier", "HOT")
            new_tier = compute_tier(last_accessed, run.get("access_count", 0))

            if old_tier != new_tier:
                store._conn.execute(
                    "UPDATE runs SET tier = ? WHERE id = ?",
                    (new_tier, run["id"])
                )
                moved[new_tier] += 1

        # Retier notes
        notes = store.get_all_notes()
        for note in notes:
            last_accessed = None
            if note.get("last_accessed_at"):
                last_accessed = datetime.fromisoformat(note["last_accessed_at"])

            old_tier = note.get("tier", "HOT")
            new_tier = compute_tier(last_accessed, note.get("access_count", 0))

            if old_tier != new_tier:
                store._conn.execute(
                    "UPDATE notes SET tier = ? WHERE id = ?",
                    (new_tier, note["id"])
                )
                moved[new_tier] += 1

        store._conn.commit()
        return moved

    except Exception as e:
        print(f"[memory] error retiering: {e}", file=sys.stderr)
        return {"HOT": 0, "WARM": 0, "COLD": 0}
