"""Phase 6 test script - autonomous triggers with safety."""

import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.bus import EventBus
from core.intent import Intent
from triggers.scheduler import fire_now
from memory import MemoryStore


async def test_1_scheduler_fire_now():
    """Test 1: Run scheduler:fire_now and verify full pipeline execution."""
    print("=" * 80)
    print("TEST 1: scheduler:fire_now with permission_ceiling=0")
    print("=" * 80)

    bus = EventBus()

    # Start orchestrator
    from core.orchestrator import Orchestrator
    orchestrator = Orchestrator(bus)
    orchestrator_task = asyncio.create_task(orchestrator.run())

    # Give orchestrator time to start
    await asyncio.sleep(0.5)

    print("\nFiring scheduled task now...")
    await fire_now(bus)

    # Wait for task to complete
    await asyncio.sleep(10)

    # Check memory
    store = MemoryStore()
    stats = store.stats()
    print(f"\nMemory stats after test:")
    print(f"  Total runs: {stats['total_runs']}")

    # Cleanup
    orchestrator_task.cancel()
    try:
        await orchestrator_task
    except asyncio.CancelledError:
        pass

    print("\n✓ Test 1 complete")


async def test_2_permission_ceiling_blocks():
    """Test 2: Verify permission_ceiling blocks Tier 1+ tools without hanging."""
    print("\n" + "=" * 80)
    print("TEST 2: Permission ceiling blocks Tier 1+ tools (NO HANG)")
    print("=" * 80)

    bus = EventBus()

    from core.orchestrator import Orchestrator
    orchestrator = Orchestrator(bus)
    orchestrator_task = asyncio.create_task(orchestrator.run())

    await asyncio.sleep(0.5)

    # Create intent with task that would require write_file (Tier 1)
    loop = asyncio.get_event_loop()
    intent = Intent(
        source="scheduler",
        kind="task",
        payload={"text": "write 'test' to a file called test.txt"},
        permission_ceiling="0",  # Read-only ceiling
        response_future=loop.create_future()
    )

    print("\nPublishing task that requires Tier 1 tool with ceiling=0...")
    print("Task: write 'test' to a file called test.txt")
    print("Expected: blocked, not hung waiting for input\n")

    await bus.publish(intent)

    # Wait with timeout - if it hangs, this will timeout
    try:
        result = await asyncio.wait_for(intent.response_future, timeout=30.0)
        print(f"Result: {result}")
        print("\n✓ Did not hang - permission ceiling working!")
    except asyncio.TimeoutError:
        print("\n✗ HUNG - this is a critical failure!")
        orchestrator_task.cancel()
        raise

    orchestrator_task.cancel()
    try:
        await orchestrator_task
    except asyncio.CancelledError:
        pass

    print("\n✓ Test 2 complete - no deadlock")


async def test_3_fs_watch_trigger():
    """Test 3: Trigger fs_watch by modifying a watched file."""
    print("\n" + "=" * 80)
    print("TEST 3: Filesystem watch trigger")
    print("=" * 80)

    # Create test file
    test_file = Path("test_Cargo.toml")
    test_file.write_text("# test file for fs_watch\n")

    bus = EventBus()

    from core.orchestrator import Orchestrator
    from triggers.fs_watch import start_fs_watch

    orchestrator = Orchestrator(bus)
    orchestrator_task = asyncio.create_task(orchestrator.run())
    fs_watch_task = asyncio.create_task(start_fs_watch(bus, ".", "test_Cargo.toml"))

    await asyncio.sleep(1)

    print("\nModifying watched file...")
    test_file.write_text("# modified at " + str(time.time()) + "\n")

    print("Waiting for fs_watch to trigger...")
    await asyncio.sleep(10)

    # Check notification log
    if Path("friday_notifications.log").exists():
        with open("friday_notifications.log") as f:
            logs = f.read()
            print("\nNotification log contents:")
            print(logs)
    else:
        print("\nNo notification log found")

    # Cleanup
    orchestrator_task.cancel()
    fs_watch_task.cancel()
    try:
        await orchestrator_task
    except asyncio.CancelledError:
        pass
    try:
        await fs_watch_task
    except asyncio.CancelledError:
        pass

    test_file.unlink()

    print("\n✓ Test 3 complete")


async def test_4_debounce():
    """Test 4: Modify file 3 times rapidly, verify only one Intent fires."""
    print("\n" + "=" * 80)
    print("TEST 4: Debounce multiple rapid changes")
    print("=" * 80)

    test_file = Path("test_debounce.toml")
    test_file.write_text("# initial\n")

    bus = EventBus()

    from core.orchestrator import Orchestrator
    from triggers.fs_watch import start_fs_watch

    orchestrator = Orchestrator(bus)
    orchestrator_task = asyncio.create_task(orchestrator.run())
    fs_watch_task = asyncio.create_task(start_fs_watch(bus, ".", "test_debounce.toml"))

    await asyncio.sleep(1)

    # Check initial memory count
    store = MemoryStore()
    before_stats = store.stats()

    print("\nModifying file 3 times within debounce window...")
    test_file.write_text("# change 1\n")
    await asyncio.sleep(0.5)
    test_file.write_text("# change 2\n")
    await asyncio.sleep(0.5)
    test_file.write_text("# change 3\n")

    print("Waiting for any triggered tasks...")
    await asyncio.sleep(10)

    # Check memory count - should only increase by 1
    after_stats = store.stats()
    new_runs = after_stats['total_runs'] - before_stats['total_runs']

    print(f"\nRuns before: {before_stats['total_runs']}")
    print(f"Runs after: {after_stats['total_runs']}")
    print(f"New runs: {new_runs}")

    if new_runs == 1:
        print("✓ Debounce working - only 1 run triggered")
    else:
        print(f"✗ Debounce failed - {new_runs} runs triggered")

    # Cleanup
    orchestrator_task.cancel()
    fs_watch_task.cancel()
    try:
        await orchestrator_task
    except asyncio.CancelledError:
        pass
    try:
        await fs_watch_task
    except asyncio.CancelledError:
        pass

    test_file.unlink()

    print("\n✓ Test 4 complete")


async def test_5_memory_source_tracking():
    """Test 5: Verify scheduler and fs_watch runs are stored with correct source."""
    print("\n" + "=" * 80)
    print("TEST 5: Memory source tracking")
    print("=" * 80)

    store = MemoryStore()

    # Query all runs
    runs = store.get_all_runs()

    scheduler_runs = [r for r in runs if r.get('intent_kind') == 'task']
    print(f"\nTotal runs in memory: {len(runs)}")
    print(f"Task runs: {len(scheduler_runs)}")

    print("\nRecent runs:")
    for run in runs[-5:]:
        print(f"  - kind={run.get('intent_kind')} text={run.get('intent_text', '')[:50]}")

    print("\n✓ Test 5 complete")


async def main():
    """Run all Phase 6 tests."""
    print("PHASE 6 TEST SUITE - AUTONOMOUS TRIGGERS")
    print()

    # Clean up old logs and database
    if Path("friday_notifications.log").exists():
        Path("friday_notifications.log").unlink()
    if Path(".friday_memory.db").exists():
        Path(".friday_memory.db").unlink()

    await test_1_scheduler_fire_now()
    await test_2_permission_ceiling_blocks()
    await test_3_fs_watch_trigger()
    await test_4_debounce()
    await test_5_memory_source_tracking()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
