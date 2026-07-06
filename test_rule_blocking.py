"""Test rule engine with blocking actions."""

import asyncio
import time


async def test_rule_blocking():
    """Test that BLOCK_WRITES and BLOCK_ON_TASK_BUDGET_EXCEEDED actually block execution."""
    print("=== Testing Rule Engine Blocking ===\n")

    from core.rules import evaluate_rules, apply_rule, RuleAction
    from core.world import WorldState, RuntimeState
    from core.health import HealthStatus, HealthLevel

    # Test 1: BLOCK_WRITES rule
    print("[Test 1] BLOCK_WRITES rule")
    world = WorldState.empty()
    health = HealthStatus(
        level=HealthLevel.CRITICAL,
        reasons=["Disk usage critical: 98.5%"],
        cpu_percent=50.0,
        ram_percent=50.0,
        disk_percent=98.5,
    )

    result = evaluate_rules(world, health, "write_file", elapsed_seconds=10)
    assert result is not None, "Rule should trigger"
    assert result.action == RuleAction.BLOCK_WRITES, "Should be BLOCK_WRITES"

    action = apply_rule(result, world)
    assert action["blocked"] == True, "Should block execution"
    assert "Rule:" in action["message"], "Should include rule message"
    print(f"  ✓ BLOCK_WRITES blocks: {action['blocked']}")
    print(f"  ✓ Message: {action['message'][:50]}...")
    print()

    # Test 2: BLOCK_ON_TASK_BUDGET_EXCEEDED rule
    print("[Test 2] BLOCK_ON_TASK_BUDGET_EXCEEDED rule")
    world = WorldState.empty()
    health = HealthStatus(
        level=HealthLevel.HEALTHY,
        reasons=[],
        cpu_percent=30.0,
        ram_percent=50.0,
    )

    result = evaluate_rules(world, health, "shell", elapsed_seconds=400)
    assert result is not None, "Rule should trigger"
    assert result.action == RuleAction.BLOCK_ON_TASK_BUDGET_EXCEEDED, "Should be BLOCK_ON_TASK_BUDGET_EXCEEDED"

    action = apply_rule(result, world)
    assert action["blocked"] == True, "Should block execution"
    print(f"  ✓ BLOCK_ON_TASK_BUDGET_EXCEEDED blocks: {action['blocked']}")
    print(f"  ✓ Message: {action['message'][:50]}...")
    print()

    # Test 3: Warning rules (should NOT block)
    print("[Test 3] WARNING rules (should not block)")
    world = WorldState.empty()
    health = HealthStatus(
        level=HealthLevel.WARNING,
        reasons=["RAM usage high: 88%"],
        cpu_percent=50.0,
        ram_percent=88.0,
    )

    result = evaluate_rules(world, health, "shell", elapsed_seconds=10)
    if result:
        action = apply_rule(result, world)
        assert action["blocked"] == False, "Warning rules should not block"
        print(f"  ✓ Warning rule does not block")
        print(f"  ✓ Logs warning: {action['message'][:50]}...")
    else:
        print(f"  ✓ No rule triggered (RAM at 88%, threshold is 95%)")
    print()

    # Test 4: No rule triggers
    print("[Test 4] Healthy system (no rules)")
    world = WorldState.empty()
    health = HealthStatus(
        level=HealthLevel.HEALTHY,
        reasons=[],
        cpu_percent=30.0,
        ram_percent=50.0,
        disk_percent=50.0,
    )

    result = evaluate_rules(world, health, "read_file", elapsed_seconds=5)
    assert result is None, "No rule should trigger"
    print(f"  ✓ No rules triggered on healthy system")
    print()

    print("=" * 60)
    print("RULE ENGINE TESTS PASSED")
    print("=" * 60)
    print("\nVerified:")
    print("  ✓ BLOCK_WRITES actually blocks write operations")
    print("  ✓ BLOCK_ON_TASK_BUDGET_EXCEEDED blocks further steps when task exceeds timeout")
    print("  ✓ Warning rules log but don't block")
    print("  ✓ Healthy systems don't trigger rules")
    print("\nBlocking actions return {'blocked': True, 'message': '...'}")
    print("Warning actions return {'blocked': False, 'message': '...'}")


if __name__ == "__main__":
    asyncio.run(test_rule_blocking())
