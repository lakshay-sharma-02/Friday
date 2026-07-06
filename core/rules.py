"""Deterministic rule engine - OS-level rules applied to system state."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from core.health import HealthStatus, HealthLevel
from core.world import WorldState


class RuleAction(Enum):
    """Actions that can be taken by rules."""
    REDUCE_CONCURRENCY = "reduce_concurrency"
    AVOID_EXPENSIVE_WORK = "avoid_expensive_work"
    BLOCK_ON_TASK_BUDGET_EXCEEDED = "block_on_task_budget_exceeded"
    BLOCK_WRITES = "block_writes"
    WARN_STALL = "warn_stall"
    CONTINUE = "continue"


@dataclass
class RuleResult:
    """Result of evaluating rules."""
    action: RuleAction
    reason: str
    details: dict


def evaluate_rules(world: WorldState, health: HealthStatus, tool_name: str, elapsed_seconds: float = 0.0) -> Optional[RuleResult]:
    """Evaluate deterministic OS-level rules against current state.

    Args:
        world: Current world state
        health: Current health status
        tool_name: Name of the tool being executed
        elapsed_seconds: How long current operation has been running

    Returns:
        RuleResult if a rule triggers, None otherwise
    """

    # Rule: RAM > 95% → reduce concurrency
    if health.ram_percent >= 95:
        return RuleResult(
            action=RuleAction.REDUCE_CONCURRENCY,
            reason=f"RAM usage critical: {health.ram_percent:.1f}%",
            details={"ram_percent": health.ram_percent}
        )

    # Rule: Battery low AND not charging → avoid expensive work
    if health.battery_percent and health.battery_percent <= 15 and not health.battery_charging:
        return RuleResult(
            action=RuleAction.AVOID_EXPENSIVE_WORK,
            reason=f"Battery critical: {health.battery_percent}% (not charging)",
            details={"battery_percent": health.battery_percent, "charging": False}
        )

    # Rule: Task budget exceeded → block further steps
    # Blocks further steps from starting once total task elapsed time exceeds threshold.
    # Does NOT kill an already-running process — a genuinely hung single command is
    # handled separately by run_shell()'s own per-command timeout in tools/shell.py,
    # which already kills via Popen + terminate()/kill().
    if tool_name == "shell" and elapsed_seconds > 300:
        return RuleResult(
            action=RuleAction.BLOCK_ON_TASK_BUDGET_EXCEEDED,
            reason=f"Task budget exceeded: {elapsed_seconds:.0f}s total elapsed",
            details={"elapsed_seconds": elapsed_seconds, "timeout": 300}
        )

    # Rule: Disk full → block write operations
    if health.disk_percent and health.disk_percent >= 98:
        if tool_name in ["write_file", "shell"]:
            return RuleResult(
                action=RuleAction.BLOCK_WRITES,
                reason=f"Disk usage critical: {health.disk_percent:.1f}%",
                details={"disk_percent": health.disk_percent}
            )

    # Rule: CPU extremely high AND current process idle → warn stall
    # If CPU is maxed but our task isn't doing anything, something may be wrong
    if health.cpu_percent >= 95:
        # Check if we have any active processes consuming CPU
        active_processes = world.processes.active_processes()
        our_cpu_usage = sum(p.cpu_percent for p in active_processes)

        if our_cpu_usage < 5.0:  # We're using < 5% CPU but system is at 95%+
            return RuleResult(
                action=RuleAction.WARN_STALL,
                reason=f"High CPU usage ({health.cpu_percent:.1f}%) but task appears idle",
                details={"system_cpu": health.cpu_percent, "our_cpu": our_cpu_usage}
            )

    return None


def apply_rule(result: RuleResult, world: WorldState) -> dict:
    """Apply a rule action to the world state.

    Args:
        result: The rule result that fired
        world: Current world state

    Returns:
        dict with 'blocked': bool and 'message': str
        If blocked=True, execution should be prevented
    """
    import sys

    if result.action == RuleAction.REDUCE_CONCURRENCY:
        # Log warning but don't alter behavior yet
        print(f"[rule] ⚠ {result.reason}", file=sys.stderr)
        print(f"[rule] Consider reducing parallel operations", file=sys.stderr)
        return {"blocked": False, "message": result.reason}

    elif result.action == RuleAction.AVOID_EXPENSIVE_WORK:
        # Log warning but don't alter behavior yet
        print(f"[rule] ⚠ {result.reason}", file=sys.stderr)
        print(f"[rule] Consider postponing expensive operations", file=sys.stderr)
        return {"blocked": False, "message": result.reason}

    elif result.action == RuleAction.WARN_STALL:
        # Log warning about potential stall
        print(f"[rule] ⚠ {result.reason}", file=sys.stderr)
        print(f"[rule] Task may be stalled - check system activity", file=sys.stderr)
        return {"blocked": False, "message": result.reason}

    elif result.action == RuleAction.BLOCK_ON_TASK_BUDGET_EXCEEDED:
        # BLOCKING ACTION - prevents further steps from starting
        print(f"[rule] ✗ {result.reason}", file=sys.stderr)
        print(f"[rule] Blocking further shell commands", file=sys.stderr)
        return {"blocked": True, "message": f"Rule: {result.reason}"}

    elif result.action == RuleAction.BLOCK_WRITES:
        # BLOCKING ACTION - will be caught by permission check in pipeline
        print(f"[rule] ✗ {result.reason}", file=sys.stderr)
        print(f"[rule] Write operations blocked", file=sys.stderr)
        return {"blocked": True, "message": f"Rule: {result.reason}"}

    return {"blocked": False, "message": ""}
