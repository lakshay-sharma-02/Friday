"""Continuous observation pipeline - observe, plan, execute, repeat."""

import sys
import os
import time
from dataclasses import replace
from core.run import PipelineRun
from core.executor import validate_plan
from core.world_manager import observe_world
from core.world import RuntimeState, WorldState
from core.health import evaluate_health, HealthLevel
from core.events import EventLog, ObservationEvent
from core.rules import evaluate_rules, apply_rule, RuleAction
from core.watchdog import ExecutionWatchdog
from agents.planner import create_plan

VERBOSE_PIPELINE = os.getenv("VERBOSE_PIPELINE") == "1"


def _build_retry_context(run: PipelineRun) -> str:
    """Build context string for retry attempt from failed execution."""
    failures = [entry for entry in run.execution_log if not entry["success"]]

    if not failures:
        return ""

    lines = ["Previous attempt failed:"]
    for entry in failures:
        lines.append(f"\nTool: {entry['tool']}")
        if entry.get("exit_code") is not None:
            lines.append(f"Exit code: {entry['exit_code']}")
        lines.append(f"Output: {entry['output']}")

    lines.append("\nTry another approach using the available tools.")

    return "\n".join(lines)


def _format_world_verbose(world: WorldState, health, events: EventLog) -> None:
    """Print human-readable world state when VERBOSE_PIPELINE is enabled."""
    if not VERBOSE_PIPELINE:
        return

    ws = world.workspace
    git_status = "not a git repo"
    if ws.is_git_repo:
        branch = ws.git_branch or "unknown"
        clean = "clean" if ws.git_clean else "dirty"
        git_status = f"git {clean}, branch {branch}"

    proj_desc = f'{ws.project_type or "unknown"} project' if ws.project_type else "no project detected"

    print(f"\n[WORLD]", file=sys.stderr)
    print(f"Workspace: {proj_desc}, {git_status}", file=sys.stderr)
    print(f"Computer: {world.computer.os}, {world.computer.logical_cores} cores, {world.computer.ram_gb}GB RAM", file=sys.stderr)

    if world.network.internet_reachable:
        print(f"Network: internet connected", file=sys.stderr)
    else:
        print(f"Network: no internet", file=sys.stderr)

    # Process info
    active_procs = world.processes.active_processes()
    if active_procs:
        print(f"Processes: {len(active_procs)} active", file=sys.stderr)

    # Runtime info
    if world.runtime.pipeline_active:
        print(f"Runtime: step {world.runtime.current_step}/{world.runtime.total_steps}, {world.runtime.elapsed_seconds:.1f}s elapsed", file=sys.stderr)

    # Health info
    health_emoji = {"healthy": "✓", "warning": "⚠", "critical": "✗"}
    level_str = health.level.value
    emoji = health_emoji.get(level_str, "?")
    print(f"Health: {emoji} {level_str}", file=sys.stderr)
    if health.reasons:
        for reason in health.reasons[:3]:
            print(f"  - {reason}", file=sys.stderr)

    # Recent events
    recent = events.recent(5)
    if recent:
        print(f"Recent Events:", file=sys.stderr)
        for event in recent:
            print(f"  - {event.description}", file=sys.stderr)

    print(file=sys.stderr)


def _determine_refresh_domains(tool_name: str) -> set[str]:
    """Determine which observation domains need refreshing after a tool execution.

    Args:
        tool_name: Name of the tool that was executed

    Returns:
        Set of domain names to refresh (workspace, network, processes)
    """
    # Git operations affect workspace
    if tool_name in ["git_status", "git_commit", "git_add"]:
        return {"workspace"}

    # Shell commands can affect workspace and spawn processes
    if tool_name == "shell":
        return {"workspace", "processes"}

    # Write operations affect workspace
    if tool_name in ["write_file", "edit_file"]:
        return {"workspace"}

    # Read operations don't require refresh
    if tool_name in ["read_file"]:
        return set()

    # Default: refresh workspace and processes for safety
    return {"workspace", "processes"}


async def _execute_step_with_observation(
    step: dict,
    run: PipelineRun,
    world: WorldState,
    health,
    events: EventLog,
    watchdog: ExecutionWatchdog,
    tracked_pids: set[int],
) -> tuple[dict, WorldState]:
    """Execute a single step and observe the result.

    Returns:
        (execution_log_entry, updated_world_state)
    """
    from tools.registry import TOOL_REGISTRY
    from core.permissions import check_permission
    import asyncio

    tool_name = step["tool"]
    args = step.get("args", {})
    description = step.get("description", "")

    print(f"\n[{tool_name}] {description}", file=sys.stderr)

    # Check permissions (pass intent for ceiling check)
    intent_for_check = getattr(run, 'intent', None)
    if not check_permission(tool_name, args, intent_for_check):
        log_entry = {
            "tool": tool_name,
            "args": args,
            "started_at": time.time(),
            "ended_at": time.time(),
            "duration": 0.0,
            "output": "Blocked: exceeds permission ceiling or user denied",
            "exit_code": None,
            "success": False,
            "skipped": True,
        }
        print("[blocked]", file=sys.stderr)
        return log_entry, world

    # Start watchdog monitoring
    watchdog.start_monitoring(tool_name)

    # Execute tool
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
            "pid": result.get("pid"),  # Track PID for shell commands
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
        }

        print(error_msg, file=sys.stderr)

    finally:
        # Stop watchdog monitoring
        watchdog.stop_monitoring()

    # Observe after execution
    refresh_domains = _determine_refresh_domains(tool_name)

    if VERBOSE_PIPELINE and refresh_domains:
        print(f"[observe] refreshing: {', '.join(refresh_domains)}", file=sys.stderr)

    # Update runtime state
    new_runtime = replace(world.runtime, last_observation_time=time.time())

    # Observe with partial refresh
    updated_world = await observe_world(
        cwd=world.workspace.cwd,
        runtime=new_runtime,
        tracked_pids=tracked_pids,
        refresh_only=refresh_domains if refresh_domains else None,
    )

    # Detect changes and generate events
    if "workspace" in refresh_domains:
        if updated_world.workspace.git_clean != world.workspace.git_clean:
            events.add(ObservationEvent.git_state_changed(
                f"Git state: {'clean' if updated_world.workspace.git_clean else 'dirty'}",
                {"clean": updated_world.workspace.git_clean}
            ))

    return log_entry, updated_world


async def run_pipeline(run: PipelineRun) -> str:
    """Execute a task pipeline with continuous observation.

    Architecture:
        Observe → Plan → Execute Step → Observe → Apply Rules → Update WorldState → Continue

    Returns:
        Summary string for the user
    """
    import asyncio
    from memory import MemoryStore

    task = run.intent.payload.get("text", "")

    # Initialize memory store
    store = MemoryStore()
    lesson_from_final_attempt = None

    # Initialize world state
    if run.world is None:
        runtime = RuntimeState(
            task_text=task,
            pipeline_active=True,
            task_start_time=time.time(),
            verbose_mode=VERBOSE_PIPELINE,
        )
        run.world = await observe_world(cwd=".", runtime=runtime)

    # Initialize event log and watchdog
    events = EventLog()
    watchdog = ExecutionWatchdog()
    tracked_pids = set()

    # Initial health check
    health = evaluate_health(run.world.network.internet_reachable)
    _format_world_verbose(run.world, health, events)

    # Memory search for relevant past attempts
    memory_results = []
    try:
        memory_results = await asyncio.to_thread(store.search, task, limit=3)
        if memory_results and VERBOSE_PIPELINE:
            print(f"[memory] found {len(memory_results)} relevant past attempts", file=sys.stderr)
    except Exception as e:
        print(f"[memory] search failed: {e}", file=sys.stderr)

    while run.retry_count <= run.max_retries:
        retry_context = ""
        if run.retry_count > 0:
            retry_context = _build_retry_context(run)
            print(f"\n[pipeline] retry {run.retry_count}/{run.max_retries}", file=sys.stderr)

        print(f"[pipeline] planning...", file=sys.stderr)

        # Plan with full world context and memory
        plan, lesson = await create_plan(task, run.world, health, events.recent(10), retry_context, memory_results)

        # Store lesson from final attempt only (whether success or failure)
        if lesson:
            lesson_from_final_attempt = lesson

        if not plan:
            return "Could not generate a valid plan for this task."

        run.plan = plan
        print(f"[pipeline] plan has {len(plan)} step(s)", file=sys.stderr)

        valid_steps = validate_plan(plan)

        if not valid_steps:
            return "Plan validation failed - no valid steps to execute."

        # Update runtime with plan info
        run.world.runtime.total_steps = len(valid_steps)

        print(f"[pipeline] executing {len(valid_steps)} step(s)...", file=sys.stderr)

        # Execute steps with continuous observation
        for i, step in enumerate(valid_steps):
            run.world.runtime.current_step = i + 1
            run.world.runtime.running_tool = step["tool"]

            # Check for long-running shell processes and kill them
            # Look for shell commands that have been running too long
            if len(run.execution_log) > 0:
                last_entry = run.execution_log[-1]
                if last_entry.get("tool") == "shell" and last_entry.get("pid"):
                    elapsed_since_start = time.time() - last_entry.get("started_at", 0)
                    if elapsed_since_start > 300:  # 5 minutes
                        from tools.shell import kill_process
                        pid = last_entry["pid"]
                        print(f"[rule] ✗ Shell process {pid} exceeded timeout ({elapsed_since_start:.0f}s)", file=sys.stderr)
                        print(f"[rule] Terminating process {pid}", file=sys.stderr)
                        killed = kill_process(pid)
                        if killed:
                            print(f"[rule] Process {pid} terminated", file=sys.stderr)

            # Check rules before execution
            rule_result = evaluate_rules(
                run.world,
                health,
                step["tool"],
                run.world.runtime.elapsed_seconds
            )

            if rule_result and rule_result.action != RuleAction.CONTINUE:
                # Apply rule and get blocking decision
                rule_action = apply_rule(rule_result, run.world)

                # Check if rule blocks execution
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
                    }
                    run.execution_log.append(log_entry)
                    continue

            # Execute step with observation
            log_entry, run.world = await _execute_step_with_observation(
                step, run, run.world, health, events, watchdog, tracked_pids
            )
            run.execution_log.append(log_entry)

            # Re-evaluate health after execution
            health = evaluate_health(run.world.network.internet_reachable)

            # Show updated world state if verbose
            if VERBOSE_PIPELINE:
                _format_world_verbose(run.world, health, events)

        # Check for failures after all steps
        failures = [entry for entry in run.execution_log if not entry["success"]]

        if not failures:
            run.status = "completed"
            run.world.runtime.pipeline_active = False

            # Store run in memory (success case)
            try:
                await asyncio.to_thread(store.put_run, run)
            except Exception as e:
                print(f"[memory] failed to store run: {e}", file=sys.stderr)

            # Store lesson if this was the final successful attempt with a lesson
            if lesson_from_final_attempt:
                try:
                    await asyncio.to_thread(store.add_note, lesson_from_final_attempt, "lesson", run.intent.id)
                    if VERBOSE_PIPELINE:
                        print(f"[memory] saved lesson: {lesson_from_final_attempt}", file=sys.stderr)
                except Exception as e:
                    print(f"[memory] failed to store lesson: {e}", file=sys.stderr)

            return f"Task completed successfully after {len(run.execution_log)} step(s)."

        if run.retry_count >= run.max_retries:
            run.status = "failed"
            run.world.runtime.pipeline_active = False

            # Store run in memory (failure case - equally important to remember)
            try:
                await asyncio.to_thread(store.put_run, run)
            except Exception as e:
                print(f"[memory] failed to store run: {e}", file=sys.stderr)

            # Store lesson if there was one from the final attempt
            if lesson_from_final_attempt:
                try:
                    await asyncio.to_thread(store.add_note, lesson_from_final_attempt, "lesson", run.intent.id)
                    if VERBOSE_PIPELINE:
                        print(f"[memory] saved lesson: {lesson_from_final_attempt}", file=sys.stderr)
                except Exception as e:
                    print(f"[memory] failed to store lesson: {e}", file=sys.stderr)

            return f"Task failed after {run.retry_count + 1} attempt(s). {len(failures)} step(s) failed."

        run.retry_count += 1

    run.status = "failed"
    run.world.runtime.pipeline_active = False

    # Store run in memory (exhausted retries case)
    try:
        await asyncio.to_thread(store.put_run, run)
    except Exception as e:
        print(f"[memory] failed to store run: {e}", file=sys.stderr)

    return "Task failed - exceeded maximum retries."
