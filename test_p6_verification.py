"""Phase P6 end-to-end verification scenarios."""

import asyncio
import time
from core import EventBus, Orchestrator
from core.intent import Intent
from memory.manager import MemoryManager
from memory import initialize_memory_subsystem


async def scenario_a():
    """Scenario A: Teaching memory influences immediate response."""
    print("\n=== Scenario A: Teaching Memory ===")

    loop = asyncio.get_event_loop()
    bus = EventBus()
    orchestrator = Orchestrator(bus)
    orchestrator_task = asyncio.create_task(orchestrator.run())

    try:
        # Step 1: Teach
        print("User: Remember that I always use uv instead of pip.")
        intent1 = Intent(kind="chat", source="test", payload={"text": "Remember that I always use uv instead of pip."}, response_future=loop.create_future())
        await bus.publish(intent1)
        response1 = await intent1.response_future
        print(f"Friday: {response1}\n")

        # Wait for extraction
        await asyncio.sleep(3)

        # Step 2: Query
        print("User: What should I use instead of pip?")
        t0 = time.perf_counter()
        intent2 = Intent(kind="chat", source="test", payload={"text": "What should I use instead of pip?"}, response_future=loop.create_future())
        await bus.publish(intent2)
        response2 = await intent2.response_future
        dt = time.perf_counter() - t0
        print(f"Friday: {response2}")
        print(f"Latency: {dt:.2f}s")

        # Check
        if "uv" in response2.lower():
            print("✓ Teaching memory applied")
        else:
            print("✗ Teaching memory NOT applied")
            print(f"Expected 'uv' in response, got: {response2}")

    finally:
        orchestrator_task.cancel()
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass


async def scenario_b():
    """Scenario B: Preference memory respected."""
    print("\n=== Scenario B: Preference Memory ===")

    loop = asyncio.get_event_loop()
    bus = EventBus()
    orchestrator = Orchestrator(bus)
    orchestrator_task = asyncio.create_task(orchestrator.run())

    try:
        # Step 1: State preference
        print("User: From now on keep answers under three sentences.")
        intent1 = Intent(kind="chat", source="test", payload={"text": "From now on keep answers under three sentences."}, response_future=loop.create_future())
        await bus.publish(intent1)
        response1 = await intent1.response_future
        print(f"Friday: {response1}\n")

        # Wait for extraction
        await asyncio.sleep(3)

        # Step 2: Ask a broad question
        print("User: Explain Rust ownership.")
        intent2 = Intent(kind="chat", source="test", payload={"text": "Explain Rust ownership."}, response_future=loop.create_future())
        await bus.publish(intent2)
        response2 = await intent2.response_future
        print(f"Friday: {response2}")

        # Count sentences (approximate)
        sentence_count = response2.count('.') + response2.count('!') + response2.count('?')
        print(f"Sentence count: {sentence_count}")

        if sentence_count <= 3:
            print("✓ Preference respected")
        else:
            print("✗ Preference NOT respected (response too long)")

    finally:
        orchestrator_task.cancel()
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass


async def scenario_c():
    """Scenario C: Memory persists across restart."""
    print("\n=== Scenario C: Memory Persistence ===")

    # Fresh manager
    manager = MemoryManager()

    print("User: What should I use instead of pip?")
    results = manager.search("What should I use instead of pip?", limit=5)

    print(f"Retrieved {len(results)} memories:")
    for r in results:
        print(f"  - [{r.get('type')}] {r.get('content')[:60]}...")

    # Check if uv memory exists
    found_uv = any("uv" in r.get("content", "").lower() for r in results)

    if found_uv:
        print("✓ Memory persisted")
    else:
        print("✗ Memory NOT found after restart")


async def scenario_d():
    """Scenario D: Simple greeting doesn't trigger extraction."""
    print("\n=== Scenario D: No Unnecessary Extraction ===")

    loop = asyncio.get_event_loop()
    bus = EventBus()
    orchestrator = Orchestrator(bus)
    orchestrator_task = asyncio.create_task(orchestrator.run())

    try:
        print("User: Hi")
        t0 = time.perf_counter()
        intent = Intent(kind="chat", source="test", payload={"text": "Hi"}, response_future=loop.create_future())
        await bus.publish(intent)
        response = await intent.response_future
        dt = time.perf_counter() - t0
        print(f"Friday: {response}")
        print(f"Latency: {dt:.2f}s")

        # Should be fast (< 5s since no extraction)
        if dt < 5.0:
            print("✓ Fast response (no extraction)")
        else:
            print(f"✗ Slow response ({dt:.2f}s, extraction may have run)")

    finally:
        orchestrator_task.cancel()
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass


async def scenario_e():
    """Scenario E: No chain-of-thought leakage."""
    print("\n=== Scenario E: No CoT Leakage ===")

    loop = asyncio.get_event_loop()
    bus = EventBus()
    orchestrator = Orchestrator(bus)
    orchestrator_task = asyncio.create_task(orchestrator.run())

    try:
        print("User: What is 2+2?")
        intent = Intent(kind="chat", source="test", payload={"text": "What is 2+2?"}, response_future=loop.create_future())
        await bus.publish(intent)
        response = await intent.response_future
        print(f"Friday: {response}")

        # Check for thinking markers
        cot_markers = ["thinking", "step 1", "step 2", "let me think", "first,", "1.", "2.", "3."]
        has_cot = any(marker in response.lower()[:100] for marker in cot_markers)

        if not has_cot:
            print("✓ No CoT leakage")
        else:
            print("✗ CoT detected in response")

    finally:
        orchestrator_task.cancel()
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass


async def main():
    """Run all verification scenarios."""
    initialize_memory_subsystem()

    print("Phase P6 Verification")
    print("=" * 60)

    await scenario_a()
    await scenario_b()
    await scenario_c()
    await scenario_d()
    await scenario_e()

    print("\n" + "=" * 60)
    print("Verification complete")


if __name__ == "__main__":
    asyncio.run(main())
