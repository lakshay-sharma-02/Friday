"""Integration test for Phase 9: Grounded Intelligence."""

import pytest
import asyncio
from core.grounded_intelligence import GroundedIntelligence
from core.truth_router import TruthSource
from core.world import WorldState, WorkspaceState, ComputerState, NetworkState
from core.world import DeveloperState, RuntimeState, ProcessState
from core.project_context import ProjectContext
from datetime import datetime


@pytest.mark.asyncio
async def test_memory_query():
    """Memory queries should answer from memory, not LLM."""
    gi = GroundedIntelligence()

    question = "What did I teach you?"
    answer, decision = await gi.answer(question)

    assert decision.source == TruthSource.MEMORY
    assert not decision.needs_tools


@pytest.mark.asyncio
async def test_workspace_query():
    """Workspace queries should answer from workspace state."""
    gi = GroundedIntelligence()

    workspace = WorkspaceState(
        cwd="/home/lakshay/Projects/Friday",
        project_type="python",
        languages=["python"],
    )
    world = WorldState(
        workspace=workspace,
        computer=ComputerState(),
        network=NetworkState(),
        developer=DeveloperState(),
        runtime=RuntimeState(),
        processes=ProcessState(),
        observed_at=datetime.now(),
    )
    project = ProjectContext(
        name="Friday",
        purpose="Agentic operating system",
        active_phase="Phase 9",
    )

    question = "What project are we building?"
    answer, decision = await gi.answer(question, world, project)

    assert decision.source == TruthSource.WORKSPACE
    assert "Friday" in answer


@pytest.mark.asyncio
async def test_system_query():
    """System queries should answer from observers."""
    gi = GroundedIntelligence()

    computer = ComputerState(
        os="Linux",
        ram_gb=16,
        logical_cores=8,
    )
    world = WorldState(
        workspace=WorkspaceState(cwd="."),
        computer=computer,
        network=NetworkState(internet_reachable=True),
        developer=DeveloperState(),
        runtime=RuntimeState(),
        processes=ProcessState(),
        observed_at=datetime.now(),
    )

    question = "How much RAM?"
    answer, decision = await gi.answer(question, world, None)

    assert decision.source == TruthSource.OBSERVERS
    assert "16" in answer or "ram" in answer.lower()


@pytest.mark.asyncio
async def test_llm_query():
    """Pure knowledge queries should use LLM."""
    gi = GroundedIntelligence()

    question = "Explain Rust ownership"
    answer, decision = await gi.answer(question)

    assert decision.source == TruthSource.LLM
    assert len(answer) > 0


@pytest.mark.asyncio
async def test_routing_info():
    """Get routing information for debugging."""
    gi = GroundedIntelligence()

    info = gi.get_routing_info("What's the current branch?")

    assert info["source"] == "git"
    assert info["needs_tools"] == True
    assert "git_status" in info["tool_hints"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
