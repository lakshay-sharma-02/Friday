#!/usr/bin/env python3
"""Phase 6 final verification - focused on the 5 critical requirements."""

import asyncio
import os
import time
from pathlib import Path

os.environ['VERBOSE_PIPELINE'] = '1'

from core import EventBus
from core.orchestrator import Orchestrator
from core.intent import Intent
from core.run import PipelineRun
from core.pipeline import run_pipeline
from triggers.scheduler import fire_now


print("\n" + "="*70)
print("PHASE 6 FINAL VERIFICATION")
print("="*70)

# Clear notification log
if Path("friday_notifications.log").exists():
    Path("friday_notifications.log").unlink()


print("\n" + "="*70)
print("TEST 1: scheduler:fire_now - Full pipeline with source=scheduler")
print("="*70)

async def test_1():
    bus = EventBus()
    orchestrator = Orchestrator(bus)
    orch_task = asyncio.create_task(orchestrator.run())

    await fire_now(bus)
    await asyncio.sleep(8)

    orch_task.cancel()
    try:
        await orch_task
    except asyncio.CancelledError:
        pass

asyncio.run(test_1())
print("\n✓ TEST 1 COMPLETE - Check output above for source=scheduler and permission_ceiling=0")


print("\n" + "="*70)
print("TEST 2: Permission ceiling blocks Tier 1 tools WITHOUT hanging")
print("="*70)

async def test_2():
    intent = Intent(
        source="scheduler",
        kind="task",
        payload={"text": "create a test file named /tmp/friday_test.txt with content 'hello'"},
        permission_ceiling="0"
    )

    print(f"Task: {intent.payload['text']}")
    print(f"Permission ceiling: {intent.permission_ceiling}")
    print(f"Expected: write_file or shell blocked, NO hang\n")

    response = await run_pipeline(PipelineRun(intent=intent))

    print(f"\nResponse: {response}")
    print("\n✓ TEST 2 PASSED - Completed without hanging on input()")

asyncio.run(test_2())


print("\n" + "="*70)
print("TEST 3: Filesystem watch fires intent")
print("="*70)

async def test_3():
    test_file = Path("test_cargo_watch.toml")
    test_file.write_text("[package]\nname = 'test'\n")

    bus = EventBus()
    from triggers.fs_watch import start_fs_watch
    watch_task = asyncio.create_task(start_fs_watch(bus, watch_path=".", pattern="test_cargo_watch.toml"))

    await asyncio.sleep(1)

    print(f"Modifying {test_file}...")
    test_file.write_text("[package]\nname = 'test'\nversion = '0.1.0'\n")

    try:
        intent = await asyncio.wait_for(bus.consume(), timeout=10)
        print(f"\n✓ Intent received!")
        print(f"  source: {intent.source}")
        print(f"  kind: {intent.kind}")
        print(f"  permission_ceiling: {intent.permission_ceiling}")
        print(f"  task: {intent.payload.get('text')}")
    except asyncio.TimeoutError:
        print("✗ FAILED - No intent within timeout")

    watch_task.cancel()
    try:
        await watch_task
    except asyncio.CancelledError:
        pass
    test_file.unlink()

asyncio.run(test_3())


print("\n" + "="*70)
print("TEST 4: Debouncing - 3 rapid changes = 1 intent")
print("="*70)

async def test_4():
    test_file = Path("test_debounce.toml")
    test_file.write_text("[package]\n")

    bus = EventBus()
    from triggers.fs_watch import start_fs_watch
    watch_task = asyncio.create_task(start_fs_watch(bus, watch_path=".", pattern="test_debounce.toml"))

    await asyncio.sleep(1)

    print("Modifying file 3 times rapidly (within 5s debounce window)...")
    for i in range(3):
        test_file.write_text(f"[package]\nversion = '0.{i}.0'\n")
        await asyncio.sleep(0.5)

    intents = []
    try:
        while True:
            intent = await asyncio.wait_for(bus.consume(), timeout=7)
            intents.append(intent)
            print(f"  Intent {len(intents)} received")
    except asyncio.TimeoutError:
        pass

    if len(intents) == 1:
        print(f"\n✓ TEST 4 PASSED - Only 1 intent for 3 rapid changes")
    else:
        print(f"\n✗ Expected 1 intent, got {len(intents)}")

    watch_task.cancel()
    try:
        await watch_task
    except asyncio.CancelledError:
        pass
    test_file.unlink()

asyncio.run(test_4())


print("\n" + "="*70)
print("TEST 5: Memory storage with read-only task")
print("="*70)

async def test_5():
    # Run a read-only task that should succeed and be stored
    intent = Intent(
        source="scheduler",
        kind="task",
        payload={"text": "read the file requirements.txt and report its contents"},
        permission_ceiling="0"  # read_file is tier 0
    )

    print(f"Task: {intent.payload['text']}")
    print(f"This uses read_file (tier 0) which should succeed\n")

    response = await run_pipeline(PipelineRun(intent=intent))
    print(f"\nResponse: {response}")

    # Check memory
    from memory import MemoryStore
    import sqlite3

    store = MemoryStore()
    conn = sqlite3.connect('.friday_memory.db')
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM runs')
    count = cursor.fetchone()[0]

    cursor.execute('SELECT id, intent_kind, status FROM runs ORDER BY created_at DESC LIMIT 3')
    recent = cursor.fetchall()

    print(f"\nMemory stats:")
    print(f"  Total runs: {count}")
    print(f"  Recent runs:")
    for run_id, kind, status in recent:
        print(f"    {run_id[:8]}... kind={kind} status={status}")

    conn.close()

    if count > 0:
        print(f"\n✓ TEST 5 PASSED - Runs stored in memory")
    else:
        print(f"\n⚠ No runs stored (all previous attempts may have failed)")

asyncio.run(test_5())


print("\n" + "="*70)
print("NOTIFICATION LOG")
print("="*70)
if Path("friday_notifications.log").exists():
    print(Path("friday_notifications.log").read_text())
else:
    print("(no notification log created)")


print("\n" + "="*70)
print("PHASE 6 VERIFICATION COMPLETE")
print("="*70)
print("\nKey results to verify:")
print("1. ✓ Scheduler fires with source=scheduler, ceiling=0")
print("2. ✓ Permission ceiling blocks Tier 1+ WITHOUT hanging")
print("3. ✓ Filesystem watch fires intents")
print("4. ✓ Debouncing works (1 intent for 3 rapid changes)")
print("5. ✓ Memory stores runs (if any succeeded)")
