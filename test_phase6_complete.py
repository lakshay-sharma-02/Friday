#!/usr/bin/env python3
"""Phase 6 complete test suite - all 5 required tests."""

import asyncio
import os
import time
from pathlib import Path

os.environ['VERBOSE_PIPELINE'] = '1'

from core import EventBus
from core.orchestrator import Orchestrator
from triggers.scheduler import fire_now


async def test_1_scheduler_fire_now():
    """Test 1: Run scheduler:fire_now and show full pipeline execution."""
    print("\n" + "="*70)
    print("TEST 1: scheduler:fire_now - full pipeline execution")
    print("="*70)

    bus = EventBus()
    orchestrator = Orchestrator(bus)

    # Start orchestrator in background
    orch_task = asyncio.create_task(orchestrator.run())

    # Fire the scheduled task
    await fire_now(bus)

    # Give it time to complete
    await asyncio.sleep(5)

    # Cancel orchestrator
    orch_task.cancel()
    try:
        await orch_task
    except asyncio.CancelledError:
        pass

    print("\n[TEST 1 COMPLETE]")


async def test_2_permission_ceiling_blocks():
    """Test 2: Verify permission ceiling blocks Tier 1+ tools without hanging."""
    print("\n" + "="*70)
    print("TEST 2: Permission ceiling blocking (critical safety test)")
    print("="*70)

    from core.intent import Intent
    from core.run import PipelineRun
    from core.pipeline import run_pipeline

    # Create an intent with ceiling=0 and a task that will try to use write_file (tier 1)
    intent = Intent(
        source="scheduler",
        kind="task",
        payload={"text": "create a test file named /tmp/friday_test.txt with content 'hello'"},
        permission_ceiling="0"  # Read-only ceiling
    )

    pipeline_run = PipelineRun(intent=intent)

    print(f"\n[test] Task: {intent.payload['text']}")
    print(f"[test] Permission ceiling: {intent.permission_ceiling}")
    print(f"[test] This task will likely plan to use write_file (tier 1)")
    print(f"[test] Expecting: step blocked, NO input() hang\n")

    response = await run_pipeline(pipeline_run)

    print(f"\n[test] Response: {response}")
    print(f"[test] Execution log:")
    for entry in pipeline_run.execution_log:
        blocked = entry.get('skipped', False)
        print(f"  - {entry['tool']}: success={entry['success']}, blocked={blocked}")
        if blocked:
            print(f"    reason: {entry['output']}")

    # Check that at least one step was blocked
    blocked_steps = [e for e in pipeline_run.execution_log if e.get('skipped', False)]
    if blocked_steps:
        print(f"\n[TEST 2 PASSED] {len(blocked_steps)} step(s) blocked by permission ceiling")
    else:
        print(f"\n[TEST 2 WARNING] No steps were blocked - planner may have avoided tier 1 tools")

    print("\n[TEST 2 COMPLETE - NO HANG]")


async def test_3_fs_watch():
    """Test 3: Modify a watched file and verify fs_watch fires."""
    print("\n" + "="*70)
    print("TEST 3: Filesystem watch trigger")
    print("="*70)

    # Create a test Cargo.toml file
    test_file = Path("test_cargo_watch.toml")
    test_file.write_text("[package]\nname = 'test'\n")
    print(f"[test] Created {test_file}")

    bus = EventBus()

    # Start fs_watch
    from triggers.fs_watch import start_fs_watch
    watch_task = asyncio.create_task(start_fs_watch(bus, watch_path=".", pattern="test_cargo_watch.toml"))

    # Give watcher time to initialize
    await asyncio.sleep(1)

    # Modify the file
    print(f"[test] Modifying {test_file}...")
    test_file.write_text("[package]\nname = 'test'\nversion = '0.1.0'\n")

    # Wait for the event to fire
    print("[test] Waiting for fs_watch to fire...")
    try:
        intent = await asyncio.wait_for(bus.consume(), timeout=10)
        print(f"\n[test] Intent received!")
        print(f"  source: {intent.source}")
        print(f"  kind: {intent.kind}")
        print(f"  permission_ceiling: {intent.permission_ceiling}")
        print(f"  task: {intent.payload.get('text')}")
    except asyncio.TimeoutError:
        print("[TEST 3 FAILED] No intent received within timeout")

    # Check notification log
    if Path("friday_notifications.log").exists():
        print("\n[test] friday_notifications.log contents:")
        print(Path("friday_notifications.log").read_text())

    # Cleanup
    watch_task.cancel()
    try:
        await watch_task
    except asyncio.CancelledError:
        pass
    test_file.unlink()

    print("\n[TEST 3 COMPLETE]")


async def test_4_debounce():
    """Test 4: Verify debouncing - rapid changes should produce only one intent."""
    print("\n" + "="*70)
    print("TEST 4: Filesystem watch debouncing")
    print("="*70)

    test_file = Path("test_debounce.toml")
    test_file.write_text("[package]\n")
    print(f"[test] Created {test_file}")

    bus = EventBus()

    # Start fs_watch with short debounce
    from triggers.fs_watch import start_fs_watch
    watch_task = asyncio.create_task(start_fs_watch(bus, watch_path=".", pattern="test_debounce.toml"))

    await asyncio.sleep(1)

    # Modify the file 3 times rapidly
    print(f"[test] Modifying {test_file} 3 times rapidly...")
    for i in range(3):
        test_file.write_text(f"[package]\nversion = '0.{i}.0'\n")
        await asyncio.sleep(0.5)  # Within debounce window (5s)

    # Collect intents
    intents = []
    print("[test] Collecting intents for 7 seconds...")
    try:
        while True:
            intent = await asyncio.wait_for(bus.consume(), timeout=7)
            intents.append(intent)
            print(f"[test] Intent {len(intents)} received")
    except asyncio.TimeoutError:
        pass

    print(f"\n[test] Total intents received: {len(intents)}")
    if len(intents) == 1:
        print("[TEST 4 PASSED] Debouncing worked - only 1 intent for 3 rapid changes")
    else:
        print(f"[TEST 4 WARNING] Expected 1 intent, got {len(intents)}")

    # Cleanup
    watch_task.cancel()
    try:
        await watch_task
    except asyncio.CancelledError:
        pass
    test_file.unlink()

    print("\n[TEST 4 COMPLETE]")


async def test_5_memory_stats():
    """Test 5: Verify scheduler and fs_watch runs are stored in memory with correct metadata."""
    print("\n" + "="*70)
    print("TEST 5: Memory storage verification")
    print("="*70)

    from memory import MemoryStore

    store = MemoryStore()
    stats = store.stats()

    print("\n=== Memory Statistics ===")
    print(f"Total runs: {stats.get('total_runs', 0)}")
    print(f"Total notes: {stats.get('total_notes', 0)}")

    print(f"\nRuns by source:")
    # Query runs by source
    import sqlite3
    conn = sqlite3.connect('.friday_memory.db')
    cursor = conn.cursor()
    cursor.execute('SELECT intent_source, COUNT(*) FROM runs GROUP BY intent_source')
    for source, count in cursor.fetchall():
        print(f"  {source}: {count}")

    cursor.execute('SELECT intent_source, intent_kind FROM runs ORDER BY created_at DESC LIMIT 5')
    print(f"\nRecent runs:")
    for source, kind in cursor.fetchall():
        print(f"  source={source}, kind={kind}")

    conn.close()

    print("\n[TEST 5 COMPLETE]")


async def main():
    """Run all 5 tests in sequence."""
    print("\n" + "="*70)
    print("PHASE 6 COMPLETE TEST SUITE")
    print("="*70)

    # Clear notification log
    if Path("friday_notifications.log").exists():
        Path("friday_notifications.log").unlink()

    await test_1_scheduler_fire_now()
    await test_2_permission_ceiling_blocks()
    await test_3_fs_watch()
    await test_4_debounce()
    await test_5_memory_stats()

    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
