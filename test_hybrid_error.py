import pytest
import asyncio
from unittest.mock import patch
from core.orchestrator import Orchestrator
from core.intent import Intent
from core.bus import EventBus
from core.run import PipelineRun

@pytest.mark.anyio
async def test_hybrid_pipeline_crash_handling():
    bus = EventBus()
    orchestrator = Orchestrator(bus)
    
    intent = Intent(kind="hybrid", payload={"text": "Summarize crashing pipeline"})
    
    # Mock run_pipeline to throw an exception
    async def mock_run_pipeline(run):
        raise RuntimeError("Disk failure simulation")
        
    # Mock call_model to just return what it was prompted with so we can inspect it
    async def mock_call_model(prompt):
        return prompt

    with patch("core.pipeline.run_pipeline", side_effect=mock_run_pipeline), \
         patch("core.orchestrator.call_model", side_effect=mock_call_model):
        
        # Start orchestrator loop in background
        task = asyncio.create_task(orchestrator.run())
        
        # Publish intent
        await bus.publish(intent)
        
        # Wait for response
        response = await intent.response_future
        
        # Clean up
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
            
        assert "CRITICAL INSTRUCTION: The pipeline FAILED" in response
        assert "CRITICAL PIPELINE FAILURE: Disk failure simulation" in response

@pytest.mark.anyio
async def test_hybrid_tool_failure_handling():
    bus = EventBus()
    orchestrator = Orchestrator(bus)
    
    intent = Intent(kind="hybrid", payload={"text": "Summarize failed tool output"})
    
    # Mock run_pipeline to simulate a successful pipeline run but failed tool
    async def mock_run_pipeline(run):
        run.status = "failed"
        run.execution_log.append({
            "tool": "read_file",
            "success": False,
            "output": "Permission denied: /root/secret.txt"
        })
        return "Task failed after 1 attempt(s)."
        
    async def mock_call_model(prompt):
        return prompt

    with patch("core.pipeline.run_pipeline", side_effect=mock_run_pipeline), \
         patch("core.orchestrator.call_model", side_effect=mock_call_model):
        
        task = asyncio.create_task(orchestrator.run())
        await bus.publish(intent)
        response = await intent.response_future
        task.cancel()
        
        assert "CRITICAL INSTRUCTION: The pipeline FAILED" in response
        assert "Task failed after 1 attempt" in response
        assert "read_file" in response
        assert "FAILED" in response
        assert "Permission denied: /root/secret.txt" in response
