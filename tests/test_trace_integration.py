"""Integration test for request tracing with real pipeline components."""

import pytest
import asyncio
from core.trace import start_trace, end_trace, get_current_trace, TraceStage
from core.trace_wrapper import enable_tracing, disable_tracing, is_tracing_enabled


def test_tracing_disabled_by_default():
    """Verify tracing is disabled by default."""
    assert is_tracing_enabled() is False


def test_enable_disable_tracing():
    """Test enabling and disabling tracing."""
    # Initially disabled
    assert is_tracing_enabled() is False

    # Enable
    enable_tracing()
    assert is_tracing_enabled() is True

    # Disable
    disable_tracing()
    assert is_tracing_enabled() is False


@pytest.mark.asyncio
async def test_trace_complete_workflow():
    """Test a complete tracing workflow simulating real Friday request."""
    # Start trace
    ctx = start_trace("what files are in this project?")

    # Stage 1: Capability routing
    ctx.start_stage(TraceStage.CAPABILITY_ROUTING, input_data={
        "query": "what files are in this project?"
    })
    ctx.set_routing(
        capability="filesystem_query",
        operation="READ",
        confidence=0.92,
        intent="list files"
    )
    ctx.end_stage(output_data={
        "capability": "filesystem_query",
        "reasoning": "query targets filesystem state"
    })

    # Stage 2: Memory search
    ctx.start_stage(TraceStage.MEMORY_SEARCH)

    # Simulate memory results
    ctx.add_memory(
        memory_id="run_789",
        memory_type="run",
        similarity=0.65,
        ranking=0.70,
        importance=0.6,
        relevance=0.55,
        content_preview="Previous file listing request",
        selected=True
    )

    ctx.end_stage(output_data={"memories_found": 1})

    # Stage 3: Evidence collection
    ctx.start_stage(TraceStage.EVIDENCE_COLLECTION)

    ctx.add_evidence("workspace", "cwd", "/home/user/project", confidence=1.0)
    ctx.add_evidence("workspace", "project_type", "Python", confidence=1.0)
    ctx.add_evidence("git", "branch", "main", confidence=1.0)

    ctx.end_stage(output_data={"evidence_items": 3})

    # Stage 4: LLM call
    ctx.start_stage(TraceStage.LLM_CALL)

    system_prompt = "You are Friday, a helpful assistant."
    evidence_block = "Project: Python project\nBranch: main"
    user_prompt = "List the files in this project."
    final_payload = f"{system_prompt}\n\n{evidence_block}\n\n{user_prompt}"

    ctx.set_prompt_trace(
        system_prompt=system_prompt,
        evidence_block=evidence_block,
        user_prompt=user_prompt,
        final_payload=final_payload,
        token_estimate=50
    )

    ctx.set_model_response(
        raw_output="Here are the files: main.py, utils.py, config.yaml",
        parsed_output=None,
        input_tokens=50,
        output_tokens=15,
        latency=0.85
    )

    ctx.end_stage(output_data={"response_length": 52})

    # Finalize
    trace = end_trace(success=True)

    # Verify trace contents
    assert trace.original_prompt == "what files are in this project?"
    assert trace.capability_selected == "filesystem_query"
    assert trace.operation_selected == "READ"
    assert trace.capability_confidence == 0.92
    assert len(trace.evidence) == 3
    assert len(trace.memories_retrieved) == 1
    assert len(trace.memories_selected) == 1
    assert len(trace.stages) == 4
    assert trace.success is True

    # Verify prompt trace
    assert trace.prompt_trace is not None
    assert "Friday" in trace.prompt_trace.system_prompt
    assert "Python" in trace.prompt_trace.evidence_block
    assert "List the files" in trace.prompt_trace.user_prompt

    # Verify model response
    assert trace.model_response is not None
    assert "main.py" in trace.model_response.raw_output
    assert trace.model_response.input_tokens == 50
    assert trace.model_response.output_tokens == 15

    # Verify no contamination
    assert len(trace.contamination_sources) == 0


@pytest.mark.asyncio
async def test_trace_contamination_detection_workflow():
    """Test contamination detection in a realistic scenario."""
    ctx = start_trace("analyze the repository")

    # Simulate a contaminated payload
    system_prompt = "You are Friday."
    evidence_block = "Project type: Python"
    user_prompt = "Analyze this repository."

    # Add contamination
    contaminated_payload = f"""
    {system_prompt}

    Previous conversation history shows we discussed this before.

    History:
    - pip install failed
    - requests library had issues

    {evidence_block}

    {user_prompt}
    """

    ctx.set_prompt_trace(
        system_prompt=system_prompt,
        evidence_block=evidence_block,
        user_prompt=user_prompt,
        final_payload=contaminated_payload,
        token_estimate=100
    )

    trace = end_trace(success=True)

    # Should detect contamination
    assert trace.contains_conversation_history is True
    assert trace.contains_unintended_memory is True
    assert len(trace.contamination_sources) > 0

    # Should have specific contamination markers
    contamination_str = str(trace.contamination_sources)
    assert "conversation_history" in contamination_str or "unintended_memory" in contamination_str


def test_trace_persistence(tmp_path):
    """Test that traces are correctly saved and can be loaded."""
    ctx = start_trace("test query")
    ctx.set_routing("test_cap", "READ", 0.88)
    ctx.add_evidence("workspace", "project", "Friday", confidence=1.0)

    trace = end_trace(success=True)

    # Save to temp directory
    trace_path = trace.save(directory=str(tmp_path))

    # Verify file exists
    assert trace_path.exists()

    # Load and verify
    import json
    loaded = json.loads(trace_path.read_text())

    assert loaded["original_prompt"] == "test query"
    assert loaded["capability_selected"] == "test_cap"
    assert loaded["success"] is True
    assert len(loaded["evidence"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
