"""Traced planner - adds request tracing to plan generation."""

import sys
from core.trace import get_current_trace, TraceStage
from agents.planner import create_plan as _original_create_plan


async def create_plan_traced(
    task: str,
    world: "WorldState",
    health: "HealthStatus",
    events: list["ObservationEvent"],
    retry_context: str = "",
    memory_results: list[dict] = None
) -> tuple[list[dict], str | None]:
    """Traced wrapper around create_plan."""
    trace = get_current_trace()

    if trace is None:
        # No trace context, call original
        return await _original_create_plan(task, world, health, events, retry_context, memory_results)

    # Start planning stage
    trace.start_stage(TraceStage.PLANNING, input_data={
        "task": task,
        "retry_context": retry_context,
        "memory_results_count": len(memory_results) if memory_results else 0
    })

    # Record memory retrieval
    if memory_results:
        from core.trace_integration import trace_memory_retrieval
        trace_memory_retrieval(None, task, memory_results)

    # Record workspace snapshot
    from core.trace_integration import trace_workspace_snapshot
    trace_workspace_snapshot(world)

    try:
        plan, lesson = await _original_create_plan(task, world, health, events, retry_context, memory_results)

        trace.end_stage(output_data={
            "plan_steps": len(plan) if plan else 0,
            "lesson": lesson
        })

        return plan, lesson

    except Exception as e:
        trace.end_stage(errors=[str(e)])
        raise


__all__ = ["create_plan_traced"]
