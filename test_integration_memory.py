"""Integration test - demonstrate memory working with real planner calls."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from memory import MemoryStore, initialize_memory_subsystem
from core.intent import Intent
from core.run import PipelineRun
from core.pipeline import run_pipeline

# Initialize memory subsystem to load models
initialize_memory_subsystem()


async def test_real_pipeline_with_memory():
    """Run real pipeline tasks and demonstrate memory integration."""
    print("=" * 60)
    print("Integration Test: Real Pipeline with Memory")
    print("=" * 60)

    store = MemoryStore()
    try:
        store._conn.execute("DELETE FROM memories")
        store._conn.execute("DELETE FROM embedding_index")
        store._conn.execute("DELETE FROM history")
        store._conn.commit()
    except Exception as e:
        print(f"Error clearing db: {e}")

    print("\n=== Part 1: Run first task (git status) ===")
    intent1 = Intent(kind="task", payload={"text": "check git status"})
    run1 = PipelineRun(intent=intent1)

    try:
        result1 = await run_pipeline(run1)
        print(f"Result: {result1}")
    except Exception as e:
        print(f"Task execution: {e}")

    # Check memory was stored
    stats1 = store.stats()
    print(f"\nMemory after task 1:")
    print(f"  Total runs: {stats1['total_runs']}")
    print(f"  Total notes: {stats1['total_notes']}")

    print("\n=== Part 2: Teach explicit note ===")
    teach_text = "always check dependencies before running build commands"
    store.add_note(content=teach_text, source="taught", source_run_id=None)
    print(f"Taught: {teach_text}")

    stats2 = store.stats()
    print(f"\nMemory after teaching:")
    print(f"  Total runs: {stats2['total_runs']}")
    print(f"  Total notes: {stats2['total_notes']}")
    print(f"  Notes by source: {stats2['notes_by_source']}")

    print("\n=== Part 3: Run similar task (git check) ===")
    intent2 = Intent(kind="task", payload={"text": "show me git repository status"})
    run2 = PipelineRun(intent=intent2)

    # This should find the first task in memory search
    results = store.search("git repository status", limit=3)
    print(f"\nMemory search found {len(results)} relevant items:")
    for r in results:
        print(f"  - {r['source']}: {r['text'][:50]}...")

    try:
        result2 = await run_pipeline(run2)
        print(f"\nResult: {result2}")
    except Exception as e:
        print(f"Task execution: {e}")

    stats3 = store.stats()
    print(f"\nFinal memory state:")
    print(f"  Total runs: {stats3['total_runs']}")
    print(f"  Total notes: {stats3['total_notes']}")
    print(f"  Runs by tier: {stats3['runs_by_tier']}")
    print(f"  Notes by tier: {stats3['notes_by_tier']}")
    print(f"  Notes by source: {stats3['notes_by_source']}")

    print("\n" + "=" * 60)
    print("Integration test complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_real_pipeline_with_memory())
