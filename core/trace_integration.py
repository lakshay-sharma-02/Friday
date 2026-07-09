"""Trace Integration - Wiring tracing into Friday's pipeline components.

This module provides instrumentation helpers for integrating tracing
into existing Friday components without modifying their core logic.
"""

import sys
from typing import Any, Optional, Callable
from core.trace import (
    get_current_trace,
    TraceStage,
    EvidenceTrace
)


def trace_capability_routing(capability: str, operation: str,
                            confidence: float, intent: str = None) -> None:
    """Record capability routing decision."""
    trace = get_current_trace()
    if trace is None:
        return

    trace.set_routing(capability, operation, confidence, intent)

    if trace.current_stage and trace.current_stage.stage == TraceStage.CAPABILITY_ROUTING:
        trace.end_stage(output_data={
            "capability": capability,
            "operation": operation,
            "confidence": confidence,
            "intent": intent
        })


def trace_memory_retrieval(memory_manager, query: str, results: list) -> None:
    """Record memory search results."""
    trace = get_current_trace()
    if trace is None:
        return

    for result in results:
        memory_id = result.get("id", "unknown")
        memory_type = result.get("source", "unknown")
        similarity = result.get("score", 0.0)
        ranking = result.get("ranking_score", similarity)
        importance = result.get("importance", 0.0)
        relevance = result.get("project_relevance", 0.0)
        content = result.get("text", result.get("content", ""))
        content_preview = content[:200] + "..." if len(content) > 200 else content
        selected = result.get("selected", True)
        rejection_reason = result.get("rejection_reason")

        trace.add_memory(
            memory_id=memory_id,
            memory_type=memory_type,
            similarity=similarity,
            ranking=ranking,
            importance=importance,
            relevance=relevance,
            content_preview=content_preview,
            selected=selected,
            rejection_reason=rejection_reason
        )


def trace_evidence_collection(evidence_bundle: "EvidenceBundle") -> None:
    """Record evidence collection from an EvidenceBundle."""
    trace = get_current_trace()
    if trace is None:
        return

    for item in evidence_bundle.items:
        trace.add_evidence(
            evidence_type=item.source.value,
            origin=item.key,
            content=item.value,
            confidence=item.confidence,
            **item.metadata
        )


def trace_workspace_snapshot(world_state: "WorldState",
                             project_context: "ProjectContext" = None) -> None:
    """Record workspace snapshot."""
    trace = get_current_trace()
    if trace is None:
        return

    workspace = {
        "cwd": world_state.workspace.cwd,
        "is_git_repo": world_state.workspace.is_git_repo,
        "project_type": world_state.workspace.project_type,
        "languages": world_state.workspace.languages,
        "package_manager": world_state.workspace.package_manager,
        "build_system": world_state.workspace.build_system,
    }

    project = {}
    if project_context:
        project = {
            "name": project_context.name,
            "purpose": project_context.purpose,
            "active_phase": project_context.active_phase,
            "entry_points": project_context.entry_points,
            "major_components": project_context.major_components,
        }

    git = {}
    if world_state.workspace.is_git_repo:
        git = {
            "branch": world_state.workspace.git_branch,
            "clean": world_state.workspace.git_clean,
            "modified_files": world_state.workspace.git_modified_files,
        }

    # Repository snapshot from evidence if available
    repo = {}

    documents = []

    trace.set_workspace_snapshot(workspace, project, git, repo, documents)


def trace_llm_call(system_prompt: str, user_prompt: str,
                   evidence_block: str = "", model_response: str = "",
                   input_tokens: int = None, output_tokens: int = None,
                   latency: float = 0.0) -> None:
    """Record LLM call details."""
    trace = get_current_trace()
    if trace is None:
        return

    # Build final payload
    final_payload = f"SYSTEM:\n{system_prompt}\n\n"
    if evidence_block:
        final_payload += f"EVIDENCE:\n{evidence_block}\n\n"
    final_payload += f"USER:\n{user_prompt}"

    # Estimate tokens (rough approximation: 1 token ~= 4 chars)
    token_estimate = len(final_payload) // 4

    trace.set_prompt_trace(
        system_prompt=system_prompt,
        evidence_block=evidence_block,
        user_prompt=user_prompt,
        final_payload=final_payload,
        token_estimate=token_estimate
    )

    if model_response:
        trace.set_model_response(
            raw_output=model_response,
            parsed_output=None,  # Can be set separately
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency=latency
        )


def trace_stage_wrapper(stage: TraceStage):
    """Decorator to automatically trace a function as a pipeline stage."""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            trace = get_current_trace()
            if trace:
                trace.start_stage(stage, input_data={
                    "args": str(args)[:200],
                    "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
                })

            try:
                result = await func(*args, **kwargs)
                if trace:
                    trace.end_stage(output_data={"result": str(result)[:200]})
                return result
            except Exception as e:
                if trace:
                    trace.end_stage(errors=[str(e)])
                raise

        def sync_wrapper(*args, **kwargs):
            trace = get_current_trace()
            if trace:
                trace.start_stage(stage, input_data={
                    "args": str(args)[:200],
                    "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
                })

            try:
                result = func(*args, **kwargs)
                if trace:
                    trace.end_stage(output_data={"result": str(result)[:200]})
                return result
            except Exception as e:
                if trace:
                    trace.end_stage(errors=[str(e)])
                raise

        # Detect if function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def print_trace_summary() -> None:
    """Print a summary of the current trace to stderr."""
    trace = get_current_trace()
    if trace is None:
        return

    print("\n[trace] Request trace summary:", file=sys.stderr)
    print(f"  Trace ID: {trace.trace.trace_id}", file=sys.stderr)
    print(f"  Capability: {trace.trace.capability_selected}", file=sys.stderr)
    print(f"  Operation: {trace.trace.operation_selected}", file=sys.stderr)
    print(f"  Evidence items: {len(trace.trace.evidence)}", file=sys.stderr)
    print(f"  Memories retrieved: {len(trace.trace.memories_retrieved)}", file=sys.stderr)
    print(f"  Memories selected: {len(trace.trace.memories_selected)}", file=sys.stderr)
    print(f"  Pipeline stages: {len(trace.trace.stages)}", file=sys.stderr)

    if trace.trace.contamination_sources:
        print(f"  ⚠ Contamination detected: {trace.trace.contamination_sources}", file=sys.stderr)
