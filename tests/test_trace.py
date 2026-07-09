"""Test for request tracing system."""

import pytest
import asyncio
from pathlib import Path
from core.trace import (
    start_trace,
    end_trace,
    get_current_trace,
    TraceStage
)


def test_trace_lifecycle():
    """Test basic trace creation and finalization."""
    # Start trace
    ctx = start_trace("test prompt")
    assert ctx is not None
    assert ctx.trace.original_prompt == "test prompt"
    assert get_current_trace() == ctx

    # Finalize
    trace = end_trace(success=True)
    assert trace is not None
    assert trace.success is True
    assert get_current_trace() is None


def test_trace_stages():
    """Test stage tracking."""
    ctx = start_trace("test")

    # Start and end a stage
    ctx.start_stage(TraceStage.CAPABILITY_ROUTING, input_data={"query": "test"})
    assert ctx.current_stage is not None
    assert ctx.current_stage.stage == TraceStage.CAPABILITY_ROUTING

    ctx.end_stage(output_data={"capability": "test_cap"})
    assert ctx.current_stage is None
    assert len(ctx.trace.stages) == 1

    stage = ctx.trace.stages[0]
    assert stage.stage == TraceStage.CAPABILITY_ROUTING
    assert stage.duration_seconds > 0

    end_trace()


def test_trace_evidence():
    """Test evidence collection."""
    ctx = start_trace("test")

    ctx.add_evidence("memory", "past_runs", "some content", confidence=0.9)
    ctx.add_evidence("workspace", "project_type", "Python", confidence=1.0)

    assert len(ctx.trace.evidence) == 2
    assert ctx.trace.evidence[0].type == "memory"
    assert ctx.trace.evidence[1].type == "workspace"

    end_trace()


def test_trace_memory():
    """Test memory tracking."""
    ctx = start_trace("test")

    ctx.add_memory(
        memory_id="mem_123",
        memory_type="run",
        similarity=0.85,
        ranking=0.90,
        importance=0.7,
        relevance=0.8,
        content_preview="previous attempt",
        selected=True
    )

    ctx.add_memory(
        memory_id="mem_456",
        memory_type="note",
        similarity=0.4,
        ranking=0.3,
        importance=0.5,
        relevance=0.2,
        content_preview="unrelated",
        selected=False,
        rejection_reason="low relevance"
    )

    assert len(ctx.trace.memories_retrieved) == 2
    assert len(ctx.trace.memories_selected) == 1
    assert len(ctx.trace.memories_rejected) == 1

    end_trace()


def test_trace_routing():
    """Test routing decision tracking."""
    ctx = start_trace("test")

    ctx.set_routing("git_status", "READ", 0.95, intent="check git")

    assert ctx.trace.capability_selected == "git_status"
    assert ctx.trace.operation_selected == "READ"
    assert ctx.trace.capability_confidence == 0.95
    assert ctx.trace.intent_classification == "check git"

    end_trace()


def test_trace_contamination_detection():
    """Test context leak detection."""
    ctx = start_trace("test")

    # Simulate payload with contamination
    payload = """
    System prompt here

    Previous conversation history shows...

    In our last chat we discussed...

    History:
    - pip install failed
    - requests library issue
    """

    ctx.set_prompt_trace(
        system_prompt="system",
        evidence_block="",
        user_prompt="test",
        final_payload=payload,
        token_estimate=100
    )

    # Should detect conversation history
    assert ctx.trace.contains_conversation_history is True
    assert ctx.trace.contains_unintended_memory is True
    assert len(ctx.trace.contamination_sources) > 0

    end_trace()


def test_trace_save(tmp_path):
    """Test saving trace to disk."""
    ctx = start_trace("test prompt")
    ctx.set_routing("test_cap", "READ", 0.9)
    ctx.add_evidence("workspace", "project", "Friday", confidence=1.0)

    trace = end_trace(success=True)

    # Save to temp directory
    trace_path = trace.save(directory=str(tmp_path))

    assert trace_path.exists()
    assert trace_path.name.startswith("trace_")
    assert trace_path.suffix == ".json"

    # Verify content
    import json
    data = json.loads(trace_path.read_text())
    assert data["original_prompt"] == "test prompt"
    assert data["capability_selected"] == "test_cap"
    assert len(data["evidence"]) == 1


def test_trace_serialization():
    """Test trace to dict/json conversion."""
    ctx = start_trace("test")
    ctx.set_routing("git", "READ", 0.95)

    trace = end_trace(success=True)

    # To dict
    data = trace.to_dict()
    assert isinstance(data, dict)
    assert data["original_prompt"] == "test"
    assert data["capability_selected"] == "git"

    # To JSON
    json_str = trace.to_json()
    assert isinstance(json_str, str)
    assert "test" in json_str


def test_nested_stages():
    """Test that stages can be started/ended in sequence."""
    ctx = start_trace("test")

    ctx.start_stage(TraceStage.CAPABILITY_ROUTING)
    ctx.end_stage()

    ctx.start_stage(TraceStage.MEMORY_SEARCH)
    ctx.end_stage()

    ctx.start_stage(TraceStage.EVIDENCE_COLLECTION)
    ctx.end_stage()

    assert len(ctx.trace.stages) == 3

    end_trace()


def test_trace_auto_stage_end():
    """Test that starting a new stage auto-ends the previous one."""
    ctx = start_trace("test")

    ctx.start_stage(TraceStage.CAPABILITY_ROUTING)
    # Don't manually end - start another stage
    ctx.start_stage(TraceStage.MEMORY_SEARCH)

    # First stage should be auto-ended
    assert len(ctx.trace.stages) == 1
    assert ctx.trace.stages[0].stage == TraceStage.CAPABILITY_ROUTING

    ctx.end_stage()
    assert len(ctx.trace.stages) == 2

    end_trace()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
