"""Demonstration of Friday's request tracing system."""

import asyncio
from core.trace import start_trace, end_trace, TraceStage
from core.trace_integration import (
    trace_capability_routing,
    trace_memory_retrieval,
    trace_evidence_collection,
    trace_workspace_snapshot,
    trace_llm_call
)


async def demo_trace():
    """Demonstrate the complete tracing workflow."""

    print("=" * 80)
    print("Friday Request Tracing Demonstration")
    print("=" * 80)

    # Start a trace
    print("\n1. Starting trace for: 'analyze this repository'")
    ctx = start_trace("analyze this repository")
    print(f"   Trace ID: {ctx.trace.trace_id}")

    # Simulate capability routing
    print("\n2. Capability routing stage...")
    ctx.start_stage(TraceStage.CAPABILITY_ROUTING, input_data={
        "query": "analyze this repository"
    })

    trace_capability_routing(
        capability="repository_analysis",
        operation="ANALYZE",
        confidence=0.95,
        intent="analyze repository"
    )
    print("   ✓ Routed to: repository_analysis")

    # Simulate memory search
    print("\n3. Memory search stage...")
    ctx.start_stage(TraceStage.MEMORY_SEARCH)

    mock_memory_results = [
        {
            "id": "run_123",
            "source": "runs",
            "score": 0.87,
            "ranking_score": 0.90,
            "importance": 0.8,
            "project_relevance": 0.85,
            "text": "Previous repository analysis completed successfully",
            "selected": True
        },
        {
            "id": "note_456",
            "source": "notes",
            "score": 0.3,
            "ranking_score": 0.2,
            "importance": 0.4,
            "project_relevance": 0.1,
            "text": "Unrelated note about something else",
            "selected": False,
            "rejection_reason": "low relevance"
        }
    ]

    trace_memory_retrieval(None, "analyze this repository", mock_memory_results)
    ctx.end_stage(output_data={"memories_found": 2, "memories_selected": 1})
    print("   ✓ Found 2 memories, selected 1")

    # Simulate evidence collection
    print("\n4. Evidence collection stage...")
    ctx.start_stage(TraceStage.EVIDENCE_COLLECTION)

    ctx.add_evidence("workspace", "project_type", "Python", confidence=1.0)
    ctx.add_evidence("workspace", "languages", ["Python"], confidence=1.0)
    ctx.add_evidence("git", "branch", "main", confidence=1.0)
    ctx.add_evidence("git", "status", "dirty", confidence=1.0)

    ctx.end_stage(output_data={"evidence_items": 4})
    print("   ✓ Collected 4 evidence items")

    # Simulate LLM call
    print("\n5. LLM call stage...")
    ctx.start_stage(TraceStage.LLM_CALL)

    system_prompt = "You are Friday, an AI assistant analyzing repositories."
    evidence_block = """
    EVIDENCE

    Workspace:
      project_type: Python
      languages: Python

    Git:
      branch: main
      status: dirty
    """
    user_prompt = "Analyze this repository and provide insights."

    trace_llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        evidence_block=evidence_block,
        model_response="This is a Python project on the main branch with uncommitted changes.",
        input_tokens=150,
        output_tokens=50,
        latency=1.23
    )

    ctx.end_stage(output_data={"response_length": 80})
    print("   ✓ LLM call completed (1.23s)")

    # Finalize trace
    print("\n6. Finalizing trace...")
    trace = end_trace(success=True)

    print(f"   ✓ Total latency: {trace.total_latency_seconds:.3f}s")
    print(f"   ✓ Pipeline stages: {len(trace.stages)}")
    print(f"   ✓ Evidence items: {len(trace.evidence)}")
    print(f"   ✓ Memories retrieved: {len(trace.memories_retrieved)}")
    print(f"   ✓ Contamination detected: {len(trace.contamination_sources)}")

    # Save trace
    trace_path = trace.save()
    print(f"\n7. Trace saved to: {trace_path}")

    # Show contamination detection
    if trace.contamination_sources:
        print(f"\n   ⚠ CONTAMINATION DETECTED:")
        for source in trace.contamination_sources:
            print(f"      - {source}")
    else:
        print(f"\n   ✓ No contamination detected")

    print("\n" + "=" * 80)
    print("Demonstration complete!")
    print("=" * 80)

    print("\nNext steps:")
    print(f"  ./friday_trace.py trace --trace {trace_path}")
    print(f"  ./friday_trace.py payload --trace {trace_path}")
    print(f"  ./friday_trace.py search requests pip --trace {trace_path}")

    return trace_path


if __name__ == "__main__":
    asyncio.run(demo_trace())
