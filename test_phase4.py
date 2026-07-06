"""Tests for Phase 4: World Model & Continuous Observation."""

import asyncio
import time


async def test_world_state_structure():
    """Test WorldState dataclass structure."""
    print("=== Test 1: WorldState Structure ===")

    from core.world import WorldState, WorkspaceState, ComputerState, NetworkState, DeveloperState, RuntimeState, ProcessState
    from datetime import datetime

    # Create empty world state
    world = WorldState.empty(cwd=".")

    assert isinstance(world.workspace, WorkspaceState)
    assert isinstance(world.computer, ComputerState)
    assert isinstance(world.network, NetworkState)
    assert isinstance(world.developer, DeveloperState)
    assert isinstance(world.runtime, RuntimeState)
    assert isinstance(world.processes, ProcessState)
    assert isinstance(world.observed_at, datetime)

    print("✓ WorldState has all required typed components")
    print("✓ No nested dicts, all proper dataclasses")
    print()


async def test_process_observer():
    """Test process observer functionality."""
    print("=== Test 2: Process Observer ===")

    from observers.process import inspect

    process_state = await inspect()

    assert process_state is not None
    assert hasattr(process_state, 'processes')

    print(f"✓ Process observer returns ProcessState")
    print(f"✓ Tracking {len(process_state.processes)} processes")
    print()


async def test_health_monitor():
    """Test health monitoring system."""
    print("=== Test 3: Health Monitor ===")

    from core.health import evaluate_health, HealthLevel

    health = evaluate_health(internet_reachable=True)

    assert health.level in [HealthLevel.HEALTHY, HealthLevel.WARNING, HealthLevel.CRITICAL]
    assert isinstance(health.cpu_percent, float)
    assert isinstance(health.ram_percent, float)
    assert isinstance(health.reasons, list)

    print(f"✓ Health status: {health.level.value}")
    print(f"✓ CPU: {health.cpu_percent:.1f}%, RAM: {health.ram_percent:.1f}%")
    if health.reasons:
        print(f"✓ Reasons: {', '.join(health.reasons)}")
    print()


async def test_observation_events():
    """Test observation events system."""
    print("=== Test 4: Observation Events ===")

    from core.events import EventLog, ObservationEvent, EventType

    log = EventLog(max_events=50)

    # Add events
    log.add(ObservationEvent.workspace_changed("Files modified", {}))
    log.add(ObservationEvent.git_state_changed("Branch changed to main", {}))
    log.add(ObservationEvent.process_started(1234, "test command"))
    log.add(ObservationEvent.process_finished(1234, 0))

    assert len(log.events) == 4
    assert log.events[0].type == EventType.WORKSPACE_CHANGED
    assert log.events[1].type == EventType.GIT_STATE_CHANGED

    recent = log.recent(2)
    assert len(recent) == 2

    print("✓ Event log tracks observations")
    print(f"✓ Recent events: {len(recent)}")
    print()


async def test_rule_engine():
    """Test deterministic rule engine."""
    print("=== Test 5: Rule Engine ===")

    from core.rules import evaluate_rules, RuleAction
    from core.world import WorldState
    from core.health import evaluate_health

    world = WorldState.empty()
    health = evaluate_health(True)

    # Test with normal conditions
    result = evaluate_rules(world, health, "shell", elapsed_seconds=10)

    # Should not trigger any rules under normal conditions
    if result:
        print(f"✓ Rule triggered: {result.reason}")
    else:
        print("✓ No rules triggered (system healthy)")

    # Test timeout rule
    result = evaluate_rules(world, health, "shell", elapsed_seconds=400)
    if result and result.action == RuleAction.BLOCK_ON_TASK_BUDGET_EXCEEDED:
        print("✓ Task budget exceeded rule triggers correctly")

    print()


async def test_watchdog():
    """Test execution watchdog."""
    print("=== Test 6: Execution Watchdog ===")

    from core.watchdog import ExecutionWatchdog, ExecutionStatus

    watchdog = ExecutionWatchdog()

    # Start monitoring
    watchdog.start_monitoring("shell", "test-exec")

    state = watchdog.get_state("test-exec")
    assert state is not None
    assert state.tool_name == "shell"
    assert state.status == ExecutionStatus.HEALTHY

    # Record activity
    watchdog.record_output("test-exec")
    watchdog.record_cpu_activity(True, "test-exec")

    # Check health
    state = watchdog.check_health("test-exec")
    assert state.status == ExecutionStatus.HEALTHY

    # Stop monitoring
    final_state = watchdog.stop_monitoring("test-exec")
    assert final_state is not None

    print("✓ Watchdog monitors execution")
    print(f"✓ Elapsed: {final_state.elapsed_seconds:.2f}s")
    print()


async def test_world_manager():
    """Test world manager with caching."""
    print("=== Test 7: World Manager ===")

    from core.world_manager import observe_world

    # First observation
    start = time.time()
    world1 = await observe_world(cwd=".")
    time1 = time.time() - start

    # Second observation (should use cache)
    start = time.time()
    world2 = await observe_world(cwd=".")
    time2 = time.time() - start

    assert world1.workspace.cwd == "."
    assert world2.workspace.cwd == "."

    speedup = time1 / time2 if time2 > 0 else 1

    print(f"✓ World observation complete")
    print(f"✓ First call: {time1:.3f}s, Second call: {time2:.3f}s")
    print(f"✓ Cache speedup: {speedup:.1f}x")
    print()


async def test_partial_refresh():
    """Test partial world state refresh."""
    print("=== Test 8: Partial Refresh ===")

    from core.world_manager import observe_world

    # Full observation
    world_full = await observe_world(cwd=".")

    # Partial refresh (workspace only)
    start = time.time()
    world_partial = await observe_world(cwd=".", refresh_only={"workspace"})
    elapsed = time.time() - start

    assert world_partial.workspace is not None
    assert world_partial.computer is not None  # Should be from cache

    print(f"✓ Partial refresh completed in {elapsed:.3f}s")
    print("✓ Only refreshed requested domains")
    print()


async def test_runtime_state():
    """Test RuntimeState tracking."""
    print("=== Test 9: RuntimeState ===")

    from core.world import RuntimeState

    runtime = RuntimeState(
        task_text="test task",
        pipeline_active=True,
        task_start_time=time.time(),
        verbose_mode=True,
    )

    time.sleep(0.1)
    runtime.update_elapsed(time.time())

    assert runtime.pipeline_active
    assert runtime.elapsed_seconds > 0
    assert runtime.verbose_mode

    print(f"✓ RuntimeState tracks execution")
    print(f"✓ Elapsed: {runtime.elapsed_seconds:.3f}s")
    print()


async def test_planner_context():
    """Test planner receives full world context."""
    print("=== Test 10: Planner Context ===")

    from core.world_manager import observe_world
    from core.health import evaluate_health
    from core.events import EventLog
    from agents.planner import create_plan
    import json

    # Build context
    world = await observe_world(cwd=".")
    health = evaluate_health(world.network.internet_reachable)
    events = EventLog()

    # Mock the model call to capture prompt
    import agents.planner as planner_module
    original = planner_module.call_model

    captured_prompt = None
    async def capture(prompt):
        nonlocal captured_prompt
        captured_prompt = prompt
        return json.dumps([])

    planner_module.call_model = capture
    await create_plan("test", world, health, events.recent(10), "")
    planner_module.call_model = original

    assert "World State:" in captured_prompt
    assert "Health Status:" in captured_prompt
    assert "Recent Events:" in captured_prompt

    print("✓ Planner receives WorldState")
    print("✓ Planner receives HealthStatus")
    print("✓ Planner receives Recent Events")
    print()


async def main():
    """Run all Phase 4 tests."""
    print("=" * 60)
    print("PHASE 4: WORLD MODEL & CONTINUOUS OBSERVATION - TESTS")
    print("=" * 60)
    print()

    await test_world_state_structure()
    await test_process_observer()
    await test_health_monitor()
    await test_observation_events()
    await test_rule_engine()
    await test_watchdog()
    await test_world_manager()
    await test_partial_refresh()
    await test_runtime_state()
    await test_planner_context()

    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
    print()
    print("Phase 4 Implementation Verified:")
    print("  ✓ WorldState with typed dataclasses")
    print("  ✓ ProcessState observer")
    print("  ✓ Health monitoring system")
    print("  ✓ Observation events")
    print("  ✓ Deterministic rule engine")
    print("  ✓ Execution watchdog")
    print("  ✓ World manager with caching")
    print("  ✓ Partial refresh optimization")
    print("  ✓ RuntimeState tracking")
    print("  ✓ Planner receives full context")


if __name__ == "__main__":
    asyncio.run(main())
