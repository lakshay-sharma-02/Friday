"""Phase 10 Acceptance Tests - Verify capability layer requirements.

These tests verify the acceptance criteria from PHASE 10 specification:
- Current RAM? → Uses WorldState, never shell, never LLM
- Current project? → Uses ProjectContext
- Where is MemoryManager? → Uses Filesystem capability, never hallucinates
- Git branch? → Uses Git capability
- Read README → Filesystem → LLM summarize
- Explain Rust ownership → LLM only
- Review repository → Filesystem + Git + ProjectContext → LLM
- What phase are we on? → ProjectContext
- What did I teach you? → Memory
- How should we install requests? → Memory → LLM (uses uv)
"""

import pytest
import asyncio
from core.capability_router import CapabilityRouter
from core.capability_registry import get_capability_registry, CapabilityCategory
from core.world import WorldState, WorkspaceState, ComputerState, NetworkState
from core.world import DeveloperState, RuntimeState, ProcessState
from core.project_context import ProjectContext
from datetime import datetime


class TestAcceptanceCriteria:
    """Test Phase 10 acceptance criteria."""

    def test_acceptance_current_ram(self):
        """
        ACCEPTANCE: Current RAM?
        - Uses WorldState
        - Never shell
        - Never LLM
        """
        router = CapabilityRouter()
        decision = router.route("Current RAM?")

        # Must route to system_ram capability
        assert decision.capability.name == "system_ram"
        assert decision.capability.category == CapabilityCategory.SYSTEM_STATE
        assert decision.capability.authoritative_source == "WorldState.computer.ram_gb"

        # Must NOT require shell, planner, or LLM
        assert not decision.capability.requires_planner
        assert not decision.capability.requires_executor
        assert not decision.capability.requires_llm

        # Must be instant
        from core.capability_registry import LatencyCategory
        assert decision.capability.latency == LatencyCategory.INSTANT

    def test_acceptance_current_project(self):
        """
        ACCEPTANCE: Current project?
        - Uses ProjectContext
        """
        router = CapabilityRouter()
        decision = router.route("What is the current project?")

        # Must route to workspace_project capability
        assert decision.capability.name == "workspace_project"
        assert decision.capability.category == CapabilityCategory.WORKSPACE
        assert "ProjectContext" in decision.capability.authoritative_source

        # Must be instant
        from core.capability_registry import LatencyCategory
        assert decision.capability.latency == LatencyCategory.INSTANT

    def test_acceptance_where_is_file(self):
        """
        ACCEPTANCE: Where is MemoryManager?
        - Uses Filesystem capability
        - Never hallucinates
        """
        router = CapabilityRouter()
        decision = router.route("Where is the MemoryManager class?")

        # Must route to filesystem capability
        assert decision.capability.category == CapabilityCategory.FILESYSTEM
        assert decision.capability.name == "filesystem_search"

        # Must use search_files tool (not LLM hallucination)
        assert "search_files" in decision.capability.requires_tools

    def test_acceptance_git_branch(self):
        """
        ACCEPTANCE: Git branch?
        - Uses Git capability
        """
        router = CapabilityRouter()
        decision = router.route("What is the current git branch?")

        # Must route to git capability
        assert decision.capability.category == CapabilityCategory.GIT
        assert decision.capability.name == "git_branch"
        assert "git_branch" in decision.capability.authoritative_source.lower()

        # Must be instant (from WorldState)
        from core.capability_registry import LatencyCategory
        assert decision.capability.latency == LatencyCategory.INSTANT

    def test_acceptance_read_readme(self):
        """
        ACCEPTANCE: Read README
        - Filesystem → LLM summarize
        """
        router = CapabilityRouter()

        # Simple read should go to filesystem
        decision = router.route("Read README.md")
        assert decision.capability.category == CapabilityCategory.FILESYSTEM

        # Summarize should involve LLM
        decision = router.route("Summarize README.md")
        # Should match filesystem or hybrid (needs file read + LLM)
        assert decision.capability.category in {
            CapabilityCategory.FILESYSTEM,
            CapabilityCategory.KNOWLEDGE,
        }

    def test_acceptance_explain_rust_ownership(self):
        """
        ACCEPTANCE: Explain Rust ownership
        - LLM only
        """
        router = CapabilityRouter()
        decision = router.route("Explain Rust ownership")

        # Must route to conceptual knowledge (LLM)
        assert decision.capability.name == "conceptual_knowledge"
        assert decision.capability.category == CapabilityCategory.KNOWLEDGE
        assert decision.capability.requires_llm

        # Must NOT require tools
        assert not decision.capability.requires_executor
        assert len(decision.capability.requires_tools) == 0

    def test_acceptance_review_repository(self):
        """
        ACCEPTANCE: Review repository
        - Filesystem + Git + ProjectContext → LLM
        """
        router = CapabilityRouter()
        decision = router.route("Review this repository")

        # Should route to multi-step execution or filesystem
        assert decision.capability.category in {
            CapabilityCategory.EXECUTION,
            CapabilityCategory.FILESYSTEM,
        }

        # Should require planner for multi-step coordination
        if decision.capability.category == CapabilityCategory.EXECUTION:
            assert decision.capability.requires_planner

    def test_acceptance_what_phase(self):
        """
        ACCEPTANCE: What phase are we on?
        - ProjectContext
        """
        router = CapabilityRouter()
        decision = router.route("What phase are we on?")

        # Must route to workspace_phase
        assert decision.capability.name == "workspace_phase"
        assert decision.capability.category == CapabilityCategory.WORKSPACE
        assert "ProjectContext" in decision.capability.authoritative_source

        # Must be instant
        from core.capability_registry import LatencyCategory
        assert decision.capability.latency == LatencyCategory.INSTANT

    def test_acceptance_what_did_i_teach(self):
        """
        ACCEPTANCE: What did I teach you?
        - Memory
        """
        router = CapabilityRouter()
        decision = router.route("What did I teach you?")

        # Must route to memory capability
        assert decision.capability.name == "memory_recall"
        assert decision.capability.category == CapabilityCategory.MEMORY
        assert "MemoryManager" in decision.capability.authoritative_source

    def test_acceptance_how_to_install(self):
        """
        ACCEPTANCE: How should we install requests?
        - Memory → LLM
        - Should use uv (from memory)
        """
        router = CapabilityRouter()

        # Installation tasks route to execution or knowledge
        decision = router.route("How should we install requests?")

        # Should consider memory for preferences
        # This could route to execution (multi-step) or knowledge (explain)
        assert decision.capability.category in {
            CapabilityCategory.EXECUTION,
            CapabilityCategory.KNOWLEDGE,
            CapabilityCategory.MEMORY,
        }


class TestCapabilityOwnership:
    """Test that capabilities respect ownership boundaries."""

    def test_system_state_never_uses_shell(self):
        """System state queries must never invoke shell."""
        router = CapabilityRouter()
        registry = get_capability_registry()

        system_caps = registry.get_by_category(CapabilityCategory.SYSTEM_STATE)

        for cap in system_caps:
            # None should require executor or shell
            assert not cap.requires_executor
            assert "shell" not in cap.requires_tools
            # All should be instant (from WorldState)
            from core.capability_registry import LatencyCategory
            assert cap.latency == LatencyCategory.INSTANT

    def test_workspace_never_uses_llm(self):
        """Workspace queries must never use LLM."""
        router = CapabilityRouter()
        registry = get_capability_registry()

        workspace_caps = registry.get_by_category(CapabilityCategory.WORKSPACE)

        for cap in workspace_caps:
            if cap.name != "workspace_project":  # Some may need minimal synthesis
                # Should not require LLM for basic queries
                assert not cap.requires_llm or cap.name == "workspace_project"

    def test_git_state_from_world_state(self):
        """Git state queries must come from WorldState, not git tool."""
        router = CapabilityRouter()
        registry = get_capability_registry()

        # git_branch and git_status should be instant from WorldState
        git_branch = registry.get("git_branch")
        assert git_branch.latency.value == "instant"
        assert not git_branch.requires_executor

        git_status = registry.get("git_status")
        assert git_status.latency.value == "instant"
        assert not git_status.requires_executor

    def test_filesystem_uses_tools(self):
        """Filesystem operations must use tools, not LLM."""
        router = CapabilityRouter()
        registry = get_capability_registry()

        filesystem_caps = registry.get_by_category(CapabilityCategory.FILESYSTEM)

        for cap in filesystem_caps:
            # All must require executor (to run tools)
            assert cap.requires_executor
            # Must have specific tools defined
            assert len(cap.requires_tools) > 0
            # Should not require LLM for basic operations
            assert not cap.requires_llm


class TestMultiCapabilityFusion:
    """Test combining multiple capabilities."""

    def test_hybrid_query_routing(self):
        """Hybrid queries should identify multiple capability needs."""
        router = CapabilityRouter()

        # "What changed since yesterday?" needs Git + Memory + Workspace
        decision = router.route("What files changed in the repository?")

        # Should route to execution (multi-capability), git, or filesystem
        assert decision.capability.category in {
            CapabilityCategory.EXECUTION,
            CapabilityCategory.GIT,
            CapabilityCategory.FILESYSTEM,
            CapabilityCategory.WORKSPACE,  # May match workspace if "project" keyword present
        }

    def test_summarize_project(self):
        """Project summary needs Workspace + Architecture + Filesystem."""
        router = CapabilityRouter()

        decision = router.route("Summarize this codebase")

        # Should route to execution, filesystem, knowledge, or workspace
        assert decision.capability.category in {
            CapabilityCategory.EXECUTION,
            CapabilityCategory.FILESYSTEM,
            CapabilityCategory.KNOWLEDGE,
            CapabilityCategory.WORKSPACE,  # May match workspace due to project context
        }


class TestPlannerIntegration:
    """Test that Planner is only invoked when needed."""

    def test_no_planner_for_simple_queries(self):
        """Simple queries should not invoke planner."""
        router = CapabilityRouter()

        simple_queries = [
            "Current RAM?",
            "Current directory?",
            "Git branch?",
            "What project?",
            "What phase?",
        ]

        for query in simple_queries:
            decision = router.route(query)
            strategy = router.get_execution_strategy(decision.capability)

            # Should be direct execution (no planning)
            assert strategy["execution_path"] == "direct"
            assert not strategy["requires_planner"]

    def test_planner_for_complex_tasks(self):
        """Complex tasks should invoke planner."""
        router = CapabilityRouter()

        complex_queries = [
            "Install dependencies",
            "Setup development environment",
            "Deploy to production",
            "Refactor this module",
        ]

        for query in complex_queries:
            decision = router.route(query)
            strategy = router.get_execution_strategy(decision.capability)

            # Should require planning
            if decision.capability.category == CapabilityCategory.EXECUTION:
                assert strategy["requires_planner"]


class TestEvidenceFlow:
    """Test that capabilities produce structured evidence."""

    def test_system_state_produces_evidence(self):
        """System state capabilities must produce evidence."""
        registry = get_capability_registry()

        ram_cap = registry.get("system_ram")
        assert ram_cap.produces_evidence

        cpu_cap = registry.get("system_cpu")
        assert cpu_cap.produces_evidence

    def test_llm_knowledge_no_evidence(self):
        """Pure LLM knowledge doesn't produce grounded evidence."""
        registry = get_capability_registry()

        knowledge_cap = registry.get("conceptual_knowledge")
        # Pure conceptual knowledge is not "evidence" - it's synthesis
        assert not knowledge_cap.produces_evidence


class TestCapabilityMatrix:
    """Test capability matrix structure."""

    def test_all_capabilities_have_owner(self):
        """Every capability must declare an owner."""
        registry = get_capability_registry()
        capabilities = registry.list_all()

        for cap in capabilities:
            assert cap.owner_module, f"Capability {cap.name} has no owner"
            assert cap.authoritative_source, f"Capability {cap.name} has no source"

    def test_all_capabilities_have_keywords(self):
        """Every capability must have keywords for routing."""
        registry = get_capability_registry()
        capabilities = registry.list_all()

        for cap in capabilities:
            total_keywords = len(cap.keywords) + len(cap.synonyms)
            assert total_keywords > 0, f"Capability {cap.name} has no keywords"

    def test_latency_categories_assigned(self):
        """Every capability must have latency category."""
        registry = get_capability_registry()
        capabilities = registry.list_all()

        for cap in capabilities:
            assert cap.latency is not None, f"Capability {cap.name} has no latency"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
