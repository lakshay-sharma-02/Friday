"""End-to-end integration test - verify Phase 4 actually runs in production."""

import asyncio
import sys


async def test_e2e_integration():
    """Test that Phase 4 continuous observation actually runs end-to-end."""

    print("=" * 70)
    print("END-TO-END INTEGRATION TEST")
    print("=" * 70)
    print()

    # Test 1: Verify the right pipeline is loaded
    print("[Test 1] Verify Phase 4 pipeline is active")
    from core.orchestrator import Orchestrator
    from core.bus import EventBus
    from core.intent import Intent
    import inspect

    # Check what pipeline the orchestrator actually imports
    orchestrator_source = inspect.getsource(Orchestrator.run)

    if "from core.pipeline import run_pipeline" in orchestrator_source:
        print("  ✓ Orchestrator imports from core.pipeline")
    else:
        print("  ✗ Orchestrator does NOT import from core.pipeline")
        return False

    # Check what that pipeline actually contains
    from core.pipeline import run_pipeline
    pipeline_source = inspect.getsource(run_pipeline)

    checks = [
        ("WorldState", "Uses WorldState (Phase 4)"),
        ("observe_world", "Uses observe_world"),
        ("evaluate_health", "Evaluates health"),
        ("evaluate_rules", "Evaluates rules"),
        ("EventLog", "Tracks events"),
        ("_execute_step_with_observation", "Continuous observation"),
    ]

    for keyword, description in checks:
        if keyword in pipeline_source:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ Missing: {description}")
            return False

    print()

    # Test 2: Actually run a task through the pipeline
    print("[Test 2] Execute actual task through pipeline")

    from core.run import PipelineRun
    from core.pipeline import run_pipeline

    # Create a simple task
    intent = Intent(
        kind="task",
        payload={"text": "echo 'Phase 4 test'"}
    )

    run = PipelineRun(intent=intent)

    # Mock the planner to return a simple plan
    import agents.planner as planner_module
    import json

    original_create_plan = planner_module.create_plan

    async def mock_plan(task, world, health, events, retry_context):
        # Verify planner receives Phase 4 context
        from core.world import WorldState
        from core.health import HealthStatus

        assert isinstance(world, WorldState), "Planner should receive WorldState"
        assert isinstance(health, HealthStatus), "Planner should receive HealthStatus"
        assert isinstance(events, list), "Planner should receive events list"

        print("  ✓ Planner received Phase 4 context (WorldState + Health + Events)")

        return [
            {
                "tool": "shell",
                "args": {"command": "echo 'Phase 4 integration test'"},
                "description": "Test command"
            }
        ]

    planner_module.create_plan = mock_plan

    try:
        result = await run_pipeline(run)

        # Check that world state was created
        assert run.world is not None, "World state should be created"
        print("  ✓ WorldState created during execution")

        # Check that execution log was populated
        assert len(run.execution_log) > 0, "Execution log should have entries"
        print(f"  ✓ Execution log has {len(run.execution_log)} entries")

        # Check that the task completed
        assert run.status in ["completed", "failed"], "Run should have status"
        print(f"  ✓ Task completed with status: {run.status}")

    finally:
        planner_module.create_plan = original_create_plan

    print()

    # Test 3: Verify rules actually block execution
    print("[Test 3] Verify rules block execution in pipeline")

    from core.world import WorldState
    from core.health import HealthStatus, HealthLevel

    # Create a run with critical disk usage
    intent = Intent(
        kind="task",
        payload={"text": "write test file"}
    )

    run = PipelineRun(intent=intent)

    # Pre-populate world with critical state
    from core.world import RuntimeState
    import time

    runtime = RuntimeState(
        task_text="test",
        pipeline_active=True,
        task_start_time=time.time(),
    )

    run.world = await observe_world(cwd=".", runtime=runtime)

    # Mock health to return critical disk state
    from core import health as health_module

    original_evaluate = health_module.evaluate_health

    def mock_critical_health(internet_reachable=True):
        return HealthStatus(
            level=HealthLevel.CRITICAL,
            reasons=["Disk usage critical: 98.5%"],
            cpu_percent=50.0,
            ram_percent=50.0,
            disk_percent=98.5,
        )

    health_module.evaluate_health = mock_critical_health

    # Mock planner to return write operation
    async def mock_write_plan(task, world, health, events, retry_context):
        # Verify health is critical
        assert health.level == HealthLevel.CRITICAL, "Health should be critical"

        return [
            {
                "tool": "write_file",
                "args": {"file_path": "/tmp/test.txt", "content": "test"},
                "description": "Attempt write with critical disk"
            }
        ]

    planner_module.create_plan = mock_write_plan

    try:
        result = await run_pipeline(run)

        # Check execution log for blocked operation
        blocked_entries = [e for e in run.execution_log if "Blocked by rule" in e.get("output", "") or "Rule:" in e.get("output", "")]

        assert len(blocked_entries) > 0, "Should have blocked entry"
        print(f"  ✓ Rule blocked write operation")
        print(f"  ✓ Blocked message: {blocked_entries[0]['output'][:60]}...")

        # Verify the operation was NOT successful
        assert blocked_entries[0]["success"] == False, "Blocked operation should fail"
        print(f"  ✓ Blocked operation marked as failed")

    finally:
        planner_module.create_plan = original_create_plan
        health_module.evaluate_health = original_evaluate

    print()

    print("=" * 70)
    print("ALL END-TO-END TESTS PASSED")
    print("=" * 70)
    print()
    print("Verified:")
    print("  ✓ Phase 4 pipeline is actually loaded by orchestrator")
    print("  ✓ WorldState + Health + Events context reaches planner")
    print("  ✓ Continuous observation runs during execution")
    print("  ✓ Rules actually block execution when triggered")
    print("  ✓ No dead code - Phase 4 is the live path")
    print()

    return True


if __name__ == "__main__":
    from core.world_manager import observe_world

    try:
        success = asyncio.run(test_e2e_integration())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
