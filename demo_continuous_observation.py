"""Demonstration of Phase 4 continuous observation in action."""

import asyncio
import os


async def demo_continuous_observation():
    """Demonstrate the continuous observation loop."""

    print("=" * 70)
    print("PHASE 4: CONTINUOUS OBSERVATION DEMO")
    print("=" * 70)
    print()

    from core.world_manager import observe_world
    from core.health import evaluate_health
    from core.events import EventLog, ObservationEvent
    from core.world import RuntimeState
    import time

    # Enable verbose mode
    os.environ['VERBOSE_PIPELINE'] = '1'

    print("[Demo] Simulating continuous observation cycle\n")

    # Initial observation
    print("─── Initial Observation ───")
    runtime = RuntimeState(
        task_text="Demo task",
        pipeline_active=True,
        current_step=0,
        total_steps=3,
        task_start_time=time.time(),
        verbose_mode=True,
    )

    world = await observe_world(cwd=".", runtime=runtime)
    health = evaluate_health(world.network.internet_reachable)
    events = EventLog()

    print(f"World observed at: {world.observed_at.strftime('%H:%M:%S')}")
    print(f"  Workspace: {world.workspace.project_type or 'none'} project")
    print(f"  Git: {'repo' if world.workspace.is_git_repo else 'not a repo'}")
    print(f"  Health: {health.level.value} (CPU: {health.cpu_percent:.1f}%, RAM: {health.ram_percent:.1f}%)")
    print(f"  Runtime: Step {world.runtime.current_step}/{world.runtime.total_steps}")
    print()

    # Simulate step 1 - git operation
    print("─── After Step 1: Git Status ───")
    time.sleep(0.1)
    world.runtime.current_step = 1
    world.runtime.running_tool = "git_status"
    world.runtime.update_elapsed(time.time())

    # Partial refresh (workspace only)
    world = await observe_world(
        cwd=".",
        runtime=world.runtime,
        refresh_only={"workspace"}
    )

    events.add(ObservationEvent.workspace_changed("Git status checked", {}))

    print(f"World observed at: {world.observed_at.strftime('%H:%M:%S')}")
    print(f"  Refreshed: workspace only")
    print(f"  Elapsed: {world.runtime.elapsed_seconds:.2f}s")
    print(f"  Events: {len(events.events)} total")
    print()

    # Simulate step 2 - shell command
    print("─── After Step 2: Shell Command ───")
    time.sleep(0.1)
    world.runtime.current_step = 2
    world.runtime.running_tool = "shell"
    world.runtime.update_elapsed(time.time())

    # Partial refresh (workspace + processes)
    world = await observe_world(
        cwd=".",
        runtime=world.runtime,
        refresh_only={"workspace", "processes"}
    )

    events.add(ObservationEvent.process_started(12345, "echo test"))
    events.add(ObservationEvent.process_finished(12345, 0))

    print(f"World observed at: {world.observed_at.strftime('%H:%M:%S')}")
    print(f"  Refreshed: workspace + processes")
    print(f"  Elapsed: {world.runtime.elapsed_seconds:.2f}s")
    print(f"  Events: {len(events.events)} total")
    print()

    # Simulate step 3 - read file (no refresh needed)
    print("─── After Step 3: Read File ───")
    time.sleep(0.1)
    world.runtime.current_step = 3
    world.runtime.running_tool = "read_file"
    world.runtime.update_elapsed(time.time())

    print(f"  No refresh needed for read operations")
    print(f"  Elapsed: {world.runtime.elapsed_seconds:.2f}s")
    print()

    # Final state
    print("─── Final State ───")
    world.runtime.pipeline_active = False

    print(f"Task completed in {world.runtime.elapsed_seconds:.2f}s")
    print(f"Total observations: {world.runtime.current_step + 1} (1 initial + {world.runtime.current_step} after each step)")
    print(f"Total events: {len(events.events)}")
    print()

    # Show event log
    print("─── Event Log ───")
    for i, event in enumerate(events.events, 1):
        print(f"  {i}. [{event.type.value}] {event.description}")
    print()

    # Architecture comparison
    print("=" * 70)
    print("ARCHITECTURE TRANSFORMATION")
    print("=" * 70)
    print()
    print("Phase 3 (One-Shot):")
    print("  Observe Once → Plan → Execute All Steps → Done")
    print()
    print("Phase 4 (Continuous):")
    print("  Observe → Plan → Execute Step → Observe → Apply Rules → Continue")
    print()
    print("Key Improvements:")
    print("  ✓ World state updates after every action")
    print("  ✓ Partial refresh for efficiency (workspace only: ~6ms)")
    print("  ✓ Health monitoring informs decisions")
    print("  ✓ Events track meaningful changes")
    print("  ✓ Rules applied deterministically")
    print("  ✓ Planner receives updated context each step")
    print()
    print("=" * 70)
    print("Friday now perceives its environment continuously.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_continuous_observation())
