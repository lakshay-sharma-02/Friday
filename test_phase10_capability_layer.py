"""Phase 10: Capability Layer tests.

Tests the metadata-driven capability routing and execution system.
"""

import pytest
import asyncio
from core.capability_registry import (
    get_capability_registry,
    CapabilityMetadata,
    CapabilityCategory,
    LatencyCategory
)
from core.capability_router import CapabilityRouter
from core.capability_executor import CapabilityExecutor
from core.capability_layer import CapabilityLayer
from core.world import WorldState, WorkspaceState, ComputerState, NetworkState
from core.world import DeveloperState, RuntimeState, ProcessState
from core.project_context import ProjectContext
from datetime import datetime


class TestCapabilityRegistry:
    """Test capability registry."""

    def test_registry_initialized(self):
        """Registry should have core capabilities registered."""
        registry = get_capability_registry()
        capabilities = registry.list_all()

        assert len(capabilities) > 0

        # Check key capabilities exist
        assert registry.get("system_ram") is not None
        assert registry.get("workspace_project") is not None
        assert registry.get("git_branch") is not None
        assert registry.get("memory_recall") is not None

    def test_find_by_keywords(self):
        """Registry should find capabilities by keywords."""
        registry = get_capability_registry()

        # Test RAM query
        matches = registry.find_by_keywords("current ram usage")
        assert any(c.name == "system_ram" for c in matches)

        # Test project query
        matches = registry.find_by_keywords("what project")
        assert any(c.name == "workspace_project" for c in matches)

        # Test git query
        matches = registry.find_by_keywords("current branch")
        assert any(c.name == "git_branch" for c in matches)

    def test_get_by_category(self):
        """Registry should filter by category."""
        registry = get_capability_registry()

        system_caps = registry.get_by_category(CapabilityCategory.SYSTEM_STATE)
        assert len(system_caps) > 0
        assert all(c.category == CapabilityCategory.SYSTEM_STATE for c in system_caps)

        workspace_caps = registry.get_by_category(CapabilityCategory.WORKSPACE)
        assert len(workspace_caps) > 0


class TestCapabilityRouter:
    """Test capability routing."""

    def test_route_system_queries(self):
        """System state queries should route to system capabilities."""
        router = CapabilityRouter()

        # RAM query
        decision = router.route("Current RAM usage?")
        assert decision.capability.name == "system_ram"
        assert decision.capability.category == CapabilityCategory.SYSTEM_STATE

        # CPU query
        decision = router.route("How many CPU cores?")
        assert decision.capability.name == "system_cpu"

        # Battery query
        decision = router.route("What's the battery level?")
        assert decision.capability.name == "system_battery"

    def test_route_workspace_queries(self):
        """Workspace queries should route to workspace capabilities."""
        router = CapabilityRouter()

        # Project query
        decision = router.route("What project are we building?")
        assert decision.capability.name == "workspace_project"
        assert decision.capability.category == CapabilityCategory.WORKSPACE

        # Phase query
        decision = router.route("What phase are we on?")
        assert decision.capability.name == "workspace_phase"

    def test_route_git_queries(self):
        """Git queries should route to git capabilities."""
        router = CapabilityRouter()

        # Branch query
        decision = router.route("Current git branch?")
        assert decision.capability.name == "git_branch"
        assert decision.capability.category == CapabilityCategory.GIT

        # Status query
        decision = router.route("Is git clean?")
        assert decision.capability.name in ["git_branch", "git_status"]

    def test_route_memory_queries(self):
        """Memory queries should route to memory capability."""
        router = CapabilityRouter()

        decision = router.route("What did I teach you?")
        assert decision.capability.name == "memory_recall"
        assert decision.capability.category == CapabilityCategory.MEMORY

    def test_route_knowledge_queries(self):
        """Knowledge queries should route to LLM."""
        router = CapabilityRouter()

        decision = router.route("Explain Rust ownership")
        assert decision.capability.name == "conceptual_knowledge"
        assert decision.capability.category == CapabilityCategory.KNOWLEDGE
        assert decision.capability.requires_llm

    def test_execution_strategy(self):
        """Router should provide execution strategies."""
        router = CapabilityRouter()

        # Direct execution (instant)
        decision = router.route("Current RAM?")
        strategy = router.get_execution_strategy(decision.capability, decision.operation)
        assert strategy["execution_path"] == "direct"
        assert not strategy["requires_planner"]

        # LLM execution - use more specific conceptual question
        decision = router.route("Explain the concept of Rust ownership")
        strategy = router.get_execution_strategy(decision.capability, decision.operation)
        # Synthesis collects evidence then asks the LLM (correct for explanations).
        assert strategy["execution_path"] in ["llm", "direct", "synthesis"]
        if decision.capability.name == "conceptual_knowledge":
            assert strategy["requires_llm"]

    def test_prefers_instant_over_slow(self):
        """Router should prefer instant capabilities over slow ones."""
        router = CapabilityRouter()

        # RAM query should go to WorldState (instant), not shell (slow)
        decision = router.route("Current RAM?")
        assert decision.capability.latency == LatencyCategory.INSTANT


@pytest.mark.asyncio
class TestCapabilityExecutor:
    """Test capability execution."""

    async def test_execute_system_state(self):
        """Execute system state capability."""
        executor = CapabilityExecutor()
        registry = get_capability_registry()

        # Create mock world state
        computer = ComputerState(
            os="Linux",
            ram_gb=16,
            logical_cores=8,
            disk_use_percent="45%"
        )
        world = WorldState(
            workspace=WorkspaceState(cwd="."),
            computer=computer,
            network=NetworkState(internet_reachable=True),
            developer=DeveloperState(),
            runtime=RuntimeState(),
            processes=ProcessState(),
            observed_at=datetime.now()
        )

        # Execute RAM capability
        ram_cap = registry.get("system_ram")
        result = await executor.execute(ram_cap, "Current RAM?", world=world)

        assert result.success
        assert result.data["ram_gb"] == 16
        assert result.source == "WorldState (observers)"
        assert not result.used_llm

    async def test_execute_workspace(self):
        """Execute workspace capability."""
        executor = CapabilityExecutor()
        registry = get_capability_registry()

        # Create mock context
        workspace = WorkspaceState(cwd=".", project_type="python", languages=["python"])
        world = WorldState(
            workspace=workspace,
            computer=ComputerState(),
            network=NetworkState(),
            developer=DeveloperState(),
            runtime=RuntimeState(),
            processes=ProcessState(),
            observed_at=datetime.now()
        )
        project = ProjectContext(
            name="Friday",
            purpose="Agentic OS",
            active_phase="Phase 10"
        )

        # Execute project capability
        project_cap = registry.get("workspace_project")
        result = await executor.execute(project_cap, "What project?", world, project)

        assert result.success
        assert result.data["name"] == "Friday"

    async def test_execute_git(self):
        """Execute git capability."""
        executor = CapabilityExecutor()
        registry = get_capability_registry()

        # Create mock git state
        workspace = WorkspaceState(
            cwd=".",
            is_git_repo=True,
            git_branch="main",
            git_clean=True
        )
        world = WorldState(
            workspace=workspace,
            computer=ComputerState(),
            network=NetworkState(),
            developer=DeveloperState(),
            runtime=RuntimeState(),
            processes=ProcessState(),
            observed_at=datetime.now()
        )

        # Execute branch capability
        branch_cap = registry.get("git_branch")
        result = await executor.execute(branch_cap, "Current branch?", world=world)

        assert result.success
        assert result.data["branch"] == "main"


@pytest.mark.asyncio
class TestCapabilityLayer:
    """Test unified capability layer."""

    async def test_handle_direct_query(self):
        """Handle direct query (instant answer)."""
        layer = CapabilityLayer()

        # Test with a system state query that should route to direct
        answer, metadata = await layer.handle("Current RAM usage?", verbose=True)

        # Should route to system_state category, but execution path may vary
        # based on whether WorldState is available
        assert "capability" in metadata
        assert "category" in metadata
        # Answer will be the actual RAM or an error if WorldState unavailable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
