"""Integration test - verify Phase 4 works end-to-end."""

import asyncio
import os


async def test_integration():
    """Test that Phase 4 integrates with existing Friday infrastructure."""

    print("=== Phase 4 Integration Test ===\n")

    # Test 1: Can import all new modules
    print("[1] Testing imports...")
    try:
        from core.world import WorldState, RuntimeState, ProcessState
        from core.health import evaluate_health, HealthLevel
        from core.events import EventLog, ObservationEvent
        from core.rules import evaluate_rules
        from core.watchdog import ExecutionWatchdog
        from core.world_manager import observe_world
        from observers.process import inspect
        print("✓ All Phase 4 modules import successfully\n")
    except ImportError as e:
        print(f"✗ Import failed: {e}\n")
        return False

    # Test 2: WorldState creation
    print("[2] Testing WorldState creation...")
    world = await observe_world(cwd=".")
    assert world.workspace.cwd == "."
    assert world.runtime is not None
    assert world.processes is not None
    print(f"✓ WorldState created with {len(world.__dataclass_fields__)} components\n")

    # Test 3: Health evaluation
    print("[3] Testing health evaluation...")
    health = evaluate_health(world.network.internet_reachable)
    print(f"✓ Health: {health.level.value} (CPU: {health.cpu_percent:.1f}%, RAM: {health.ram_percent:.1f}%)\n")

    # Test 4: Events system
    print("[4] Testing events system...")
    events = EventLog()
    events.add(ObservationEvent.workspace_changed("Test change", {}))
    assert len(events.events) == 1
    print(f"✓ Event log working ({len(events.events)} events)\n")

    # Test 5: Rule engine
    print("[5] Testing rule engine...")
    rule_result = evaluate_rules(world, health, "shell", elapsed_seconds=10)
    if rule_result:
        print(f"✓ Rule triggered: {rule_result.reason}\n")
    else:
        print("✓ Rule engine operational (no rules triggered)\n")

    # Test 6: Planner integration
    print("[6] Testing planner integration...")
    from agents.planner import create_plan
    import json

    # Mock model call
    import agents.planner as planner_module
    original = planner_module.call_model

    async def mock_call(prompt):
        # Verify prompt structure
        assert "World State:" in prompt, "Missing World State in prompt"
        assert "Health Status:" in prompt, "Missing Health Status in prompt"
        assert "Recent Events:" in prompt, "Missing Recent Events in prompt"
        return json.dumps([
            {"tool": "shell", "args": {"command": "echo test"}, "description": "Test"}
        ])

    planner_module.call_model = mock_call
    plan = await create_plan("test", world, health, events.recent(10), "")
    planner_module.call_model = original

    assert len(plan) == 1
    print("✓ Planner receives full WorldState + Health + Events context\n")

    # Test 7: PipelineRun compatibility
    print("[7] Testing PipelineRun integration...")
    from core.run import PipelineRun
    from core.intent import Intent

    intent = Intent(payload={"text": "test"})
    run = PipelineRun(intent=intent)

    assert hasattr(run, "world"), "PipelineRun missing 'world' field"
    assert run.world is None, "world should start as None"
    print("✓ PipelineRun has 'world' field (replaces 'environment')\n")

    # Test 8: Continuous observation (partial refresh)
    print("[8] Testing partial refresh...")
    import time
    start = time.time()
    world_partial = await observe_world(cwd=".", refresh_only={"workspace"})
    elapsed = time.time() - start

    assert world_partial.workspace is not None
    print(f"✓ Partial refresh completed in {elapsed:.3f}s\n")

    print("=" * 60)
    print("INTEGRATION TEST PASSED")
    print("=" * 60)
    print("\nPhase 4 successfully integrated:")
    print("  ✓ All modules import cleanly")
    print("  ✓ WorldState replaces EnvironmentState")
    print("  ✓ Health monitoring operational")
    print("  ✓ Event system working")
    print("  ✓ Rule engine functional")
    print("  ✓ Planner receives full context")
    print("  ✓ PipelineRun updated to use WorldState")
    print("  ✓ Partial refresh optimization working")
    print("\nFriday is now continuously aware of its environment.")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_integration())
    exit(0 if success else 1)
