"""Continuous observation pipeline - observe, plan, execute, repeat."""

import sys
import os
import time
from dataclasses import replace
from core.run import PipelineRun
from core.plan_validation import validate_and_prepare_plan
from core.world_manager import observe_world
from core.world import RuntimeState, WorldState
from core.health import evaluate_health, HealthLevel
from core.events import EventLog
from core.watchdog import ExecutionWatchdog
from agents.planner import create_plan

VERBOSE_PIPELINE = os.getenv("VERBOSE_PIPELINE") == "1"


def _reflect_on_execution(run: PipelineRun, world: WorldState, timings: dict) -> None:
    """Phase 12: Engineering Reflection - identify improvement opportunities."""
    from core.reflection import EngineeringReflection
    from core.backlog import EngineeringBacklog

    reflection = EngineeringReflection()
    issue = reflection.reflect(run, world, timings)

    if issue:
        backlog = EngineeringBacklog()
        task = backlog.record_issue(issue)
        if task.occurrences == 1:
            print(f"[reflection] identified issue: {issue.layer} - {issue.reason}", file=sys.stderr)
        else:
            print(f"[reflection] recurring issue (x{task.occurrences}): {issue.layer} - {issue.reason}", file=sys.stderr)


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


async def run_pipeline(run: PipelineRun) -> str:
    """Execute a task pipeline with continuous observation.

    Architecture:
        Observe → Plan → Execute Step → Observe → Apply Rules → Update WorldState → Continue

    Returns:
        Summary string for the user
    """
    import asyncio

    task = run.intent.payload.get("text", "")

    # Initialize memory manager
    from memory.manager import MemoryManager
    memory_manager = MemoryManager()
    lesson_from_final_attempt = None

    # Initialize world state
    t_observe_start = time.perf_counter()
    if run.world is None:
        runtime = RuntimeState(
            task_text=task,
            pipeline_active=True,
            task_start_time=time.time(),
            verbose_mode=VERBOSE_PIPELINE,
        )
        run.world = await observe_world(cwd=".", runtime=runtime)
    t_observe = time.perf_counter() - t_observe_start

    # Initialize event log and watchdog
    events = EventLog()
    watchdog = ExecutionWatchdog()
    tracked_pids = set()

    # Initial health check
    t_health_start = time.perf_counter()
    health = evaluate_health(run.world.network.internet_reachable)
    _format_world_verbose(run.world, health, events)
    t_health = time.perf_counter() - t_health_start

    # Memory search for relevant past attempts
    t_memory_search_start = time.perf_counter()
    memory_results = []
    try:
        # Retrieve relevant past experiences using MemoryManager
        memory_results = await asyncio.to_thread(memory_manager.search, task, limit=3)
        if memory_results and VERBOSE_PIPELINE:
            print(f"[memory] found {len(memory_results)} relevant past attempts", file=sys.stderr)
    except Exception as e:
        print(f"[memory] search failed: {e}", file=sys.stderr)
    t_memory_search = time.perf_counter() - t_memory_search_start

    while run.retry_count <= run.max_retries:
        retry_context = ""
        if run.retry_count > 0:
            retry_context = _build_retry_context(run)
            print(f"\n[pipeline] retry {run.retry_count}/{run.max_retries}", file=sys.stderr)

        print(f"[pipeline] planning...", file=sys.stderr)

        # Plan with full world context and memory
        t_plan_start = time.perf_counter()
        plan, lesson = await create_plan(task, run.world, health, events.recent(10), retry_context, memory_results)
        t_plan = time.perf_counter() - t_plan_start

        # Store lesson from final attempt only (whether success or failure)
        if lesson:
            lesson_from_final_attempt = lesson

        if not plan:
            print(f"[pipeline] timing breakdown: observe={t_observe:.2f}s health={t_health:.2f}s memory_search={t_memory_search:.2f}s plan={t_plan:.2f}s", file=sys.stderr)
            return "Could not generate a valid plan for this task."

        run.plan = plan
        print(f"[pipeline] plan has {len(plan)} step(s)", file=sys.stderr)

        # Validate + repair + risk-tag before anything reaches the executor.
        t_validate_start = time.perf_counter()
        validation = validate_and_prepare_plan(plan)
        t_validate = time.perf_counter() - t_validate_start
        if not validation["accepted"]:
            detail = "; ".join(
                f"step {e['step']}: {e['error']}" for e in validation["errors"]
            )
            print(f"[pipeline] plan rejected: {detail}", file=sys.stderr)
            print(f"[pipeline] timing breakdown: observe={t_observe:.2f}s health={t_health:.2f}s memory_search={t_memory_search:.2f}s plan={t_plan:.2f}s validate={t_validate:.2f}s", file=sys.stderr)
            return f"Plan rejected: {validation['message']} ({detail})"

        for r in validation["repairs"]:
            print(f"[pipeline] repaired step {r['step']}: {r['repairs']}", file=sys.stderr)

        valid_steps = validation["steps"]
        run.plan_risk_level = validation["risk_level"]

        if not valid_steps:
            print(f"[pipeline] timing breakdown: observe={t_observe:.2f}s health={t_health:.2f}s memory_search={t_memory_search:.2f}s plan={t_plan:.2f}s validate={t_validate:.2f}s", file=sys.stderr)
            return "Plan validation failed - no valid steps to execute."

        # Update runtime with plan info
        run.world.runtime.total_steps = len(valid_steps)

        print(f"[pipeline] executing {len(valid_steps)} step(s)...", file=sys.stderr)

        # Delegate execution loop to Executor
        from core.executor import execute_plan
        t_execute_start = time.perf_counter()
        health = await execute_plan(
            valid_steps, run, health, events, watchdog, tracked_pids
        )
        t_execute = time.perf_counter() - t_execute_start

        # Check for failures after all steps
        failures = [entry for entry in run.execution_log if not entry["success"]]

        if not failures:
            run.status = "completed"
            run.world.runtime.pipeline_active = False

            # Process run for history and admission
            t_process_start = time.perf_counter()
            await asyncio.to_thread(memory_manager.process_run, run, lesson_from_final_attempt)
            t_process = time.perf_counter() - t_process_start

            # Phase 12: Engineering Reflection
            t_reflect_start = time.perf_counter()
            _reflect_on_execution(run, run.world, {
                "observe": t_observe,
                "health": t_health,
                "memory_search": t_memory_search,
                "plan": t_plan,
                "validate": t_validate,
                "execute": t_execute,
                "process": t_process
            })
            t_reflect = time.perf_counter() - t_reflect_start

            print(f"[pipeline] timing breakdown: observe={t_observe:.2f}s health={t_health:.2f}s memory_search={t_memory_search:.2f}s plan={t_plan:.2f}s validate={t_validate:.2f}s execute={t_execute:.2f}s process={t_process:.2f}s reflect={t_reflect:.2f}s", file=sys.stderr)
            return f"Task completed successfully after {len(run.execution_log)} step(s)."

        if run.retry_count >= run.max_retries:
            run.status = "failed"
            run.world.runtime.pipeline_active = False

            # Process run for history and admission (failure case)
            t_process_start = time.perf_counter()
            await asyncio.to_thread(memory_manager.process_run, run, lesson_from_final_attempt)
            t_process = time.perf_counter() - t_process_start

            # Phase 12: Engineering Reflection
            t_reflect_start = time.perf_counter()
            _reflect_on_execution(run, run.world, {
                "observe": t_observe,
                "health": t_health,
                "memory_search": t_memory_search,
                "plan": t_plan,
                "validate": t_validate,
                "execute": t_execute,
                "process": t_process
            })
            t_reflect = time.perf_counter() - t_reflect_start

            print(f"[pipeline] timing breakdown: observe={t_observe:.2f}s health={t_health:.2f}s memory_search={t_memory_search:.2f}s plan={t_plan:.2f}s validate={t_validate:.2f}s execute={t_execute:.2f}s process={t_process:.2f}s reflect={t_reflect:.2f}s", file=sys.stderr)
            return f"Task failed after {run.retry_count + 1} attempt(s). {len(failures)} step(s) failed."

        run.retry_count += 1

    run.status = "failed"
    run.world.runtime.pipeline_active = False

    # Process run for history and admission (exhausted retries)
    t_process_start = time.perf_counter()
    await asyncio.to_thread(memory_manager.process_run, run, lesson_from_final_attempt)
    t_process = time.perf_counter() - t_process_start

    # Phase 12: Engineering Reflection
    t_reflect_start = time.perf_counter()
    _reflect_on_execution(run, run.world, {
        "observe": t_observe,
        "health": t_health,
        "memory_search": t_memory_search,
        "plan": t_plan,
        "process": t_process
    })
    t_reflect = time.perf_counter() - t_reflect_start

    print(f"[pipeline] timing breakdown: observe={t_observe:.2f}s health={t_health:.2f}s memory_search={t_memory_search:.2f}s plan={t_plan:.2f}s process={t_process:.2f}s reflect={t_reflect:.2f}s", file=sys.stderr)
    return "Task failed - exceeded maximum retries."
