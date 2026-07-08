"""Execution engine."""

import sys
import time
import asyncio
from dataclasses import replace
from typing import Any

from tools.registry import TOOL_REGISTRY
from core.plan_validation import verify_execution_guards
from core.world import WorldState
from core.events import EventLog, ObservationEvent
from core.health import evaluate_health
from core.watchdog import ExecutionWatchdog
from core.rules import evaluate_rules, apply_rule, RuleAction
from core.world_manager import observe_world


def _determine_refresh_domains(tool_name: str) -> set[str]:
    """Determine which observation domains need refreshing after a tool execution."""
    if tool_name in ["git_status", "git_commit", "git_add"]:
        return {"workspace"}
    if tool_name == "shell":
        return {"workspace", "processes"}
    if tool_name in ["write_file", "edit_file"]:
        return {"workspace"}
    if tool_name in ["read_file"]:
        return set()
    return {"workspace", "processes"}


async def _execute_step_with_observation(
    step: dict,
    run: Any,
    world: WorldState,
    health,
    events: EventLog,
    watchdog: ExecutionWatchdog,
    tracked_pids: set[int],
) -> tuple[dict, WorldState]:
    """Execute a single step and observe the result."""
    tool_name = step["tool"]
    args = step.get("args", {})
    description = step.get("description", "")
    risk_level = step.get("risk_level")

    print(f"\n[{tool_name}] {description}" + (f" [risk:{risk_level}]" if risk_level else ""), file=sys.stderr)

    intent_for_check = getattr(run, 'intent', None)
    ok, err_msg = verify_execution_guards(step, intent_for_check, world)
    
    if not ok:
        log_entry = {
            "tool": tool_name,
            "args": args,
            "started_at": time.time(),
            "ended_at": time.time(),
            "duration": 0.0,
            "output": err_msg,
            "exit_code": None,
            "success": False,
            "skipped": True,
            "risk_level": risk_level,
        }
        print(f"[blocked] {err_msg}", file=sys.stderr)
        return log_entry, world

    watchdog.start_monitoring(tool_name)
    handler = TOOL_REGISTRY[tool_name]["handler"]

    t0 = time.time()
    try:
        result = await asyncio.to_thread(handler, **args)
        t1 = time.time()

        log_entry = {
            "tool": tool_name,
            "args": args,
            "started_at": t0,
            "ended_at": t1,
            "duration": t1 - t0,
            "output": result.get("output", ""),
            "exit_code": result.get("exit_code"),
            "success": result.get("success", False),
            "pid": result.get("pid"),
            "risk_level": risk_level,
        }

        print(result.get("output", ""))
        if not result.get("success"):
            print(f"[failed: exit_code={result.get('exit_code')}]", file=sys.stderr)

    except Exception as e:
        t1 = time.time()
        error_msg = f"Executor error: {str(e)}"
        log_entry = {
            "tool": tool_name,
            "args": args,
            "started_at": t0,
            "ended_at": t1,
            "duration": t1 - t0,
            "output": error_msg,
            "exit_code": None,
            "success": False,
            "risk_level": risk_level,
        }
        print(error_msg, file=sys.stderr)

    finally:
        watchdog.stop_monitoring()

    refresh_domains = _determine_refresh_domains(tool_name)
    verbose_mode = getattr(run.world.runtime, 'verbose_mode', False)

    if verbose_mode and refresh_domains:
        print(f"[observe] refreshing: {', '.join(refresh_domains)}", file=sys.stderr)

    new_runtime = replace(world.runtime, last_observation_time=time.time())

    updated_world = await observe_world(
        cwd=world.workspace.cwd,
        runtime=new_runtime,
        tracked_pids=tracked_pids,
        refresh_only=refresh_domains if refresh_domains else None,
    )

    if "workspace" in refresh_domains:
        if updated_world.workspace.git_clean != world.workspace.git_clean:
            events.add(ObservationEvent.git_state_changed(
                f"Git state: {'clean' if updated_world.workspace.git_clean else 'dirty'}",
                {"clean": updated_world.workspace.git_clean}
            ))

    return log_entry, updated_world


async def execute_plan(
    valid_steps: list[dict],
    run: Any,
    health: Any,
    events: EventLog,
    watchdog: ExecutionWatchdog,
    tracked_pids: set[int]
) -> Any:
    """Execute a validated plan with continuous observation and rule checking.
    
    Returns:
        updated health
    """
    from core.pipeline import _format_world_verbose
    
    verbose_mode = getattr(run.world.runtime, 'verbose_mode', False)
    
    for i, step in enumerate(valid_steps):
        run.world.runtime.current_step = i + 1
        run.world.runtime.running_tool = step["tool"]

        if len(run.execution_log) > 0:
            last_entry = run.execution_log[-1]
            if last_entry.get("tool") == "shell" and last_entry.get("pid"):
                elapsed_since_start = time.time() - last_entry.get("started_at", 0)
                if elapsed_since_start > 300:
                    from tools.shell import kill_process
                    pid = last_entry["pid"]
                    print(f"[rule] ✗ Shell process {pid} exceeded timeout ({elapsed_since_start:.0f}s)", file=sys.stderr)
                    print(f"[rule] Terminating process {pid}", file=sys.stderr)
                    killed = kill_process(pid)
                    if killed:
                        print(f"[rule] Process {pid} terminated", file=sys.stderr)

        rule_result = evaluate_rules(
            run.world,
            health,
            step["tool"],
            run.world.runtime.elapsed_seconds
        )

        if rule_result and rule_result.action != RuleAction.CONTINUE:
            rule_action = apply_rule(rule_result, run.world)
            if rule_action.get("blocked", False):
                log_entry = {
                    "tool": step["tool"],
                    "args": step.get("args", {}),
                    "started_at": time.time(),
                    "ended_at": time.time(),
                    "duration": 0.0,
                    "output": rule_action["message"],
                    "exit_code": None,
                    "success": False,
                    "risk_level": step.get("risk_level"),
                }
                run.execution_log.append(log_entry)
                continue

        log_entry, run.world = await _execute_step_with_observation(
            step, run, run.world, health, events, watchdog, tracked_pids
        )
        run.execution_log.append(log_entry)

        health = evaluate_health(run.world.network.internet_reachable)

        if verbose_mode:
            _format_world_verbose(run.world, health, events)
            
    return health
