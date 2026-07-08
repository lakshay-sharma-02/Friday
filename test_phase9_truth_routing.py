"""Phase 9: Truth Router validation tests."""

import pytest
from core.truth_router import TruthRouter, TruthSource
from core.evidence import (
    Evidence,
    EvidenceBundle,
    EvidenceSource,
    collect_workspace_evidence,
    collect_git_evidence,
    collect_system_evidence,
)
from core.project_context import ProjectContext
from core.world import WorldState, WorkspaceState, ComputerState, NetworkState
from datetime import datetime


class TestTruthRouter:
    """Test truth source routing."""

    def setup_method(self):
        self.router = TruthRouter()

    def test_memory_routing(self):
        """Memory questions route to MEMORY source."""
        questions = [
            "What's my name?",
            "What did I teach you?",
            "Do you remember what I said?",
            "My preference is X",
        ]
        for q in questions:
            decision = self.router.route(q)
            assert decision.source == TruthSource.MEMORY
            assert decision.confidence >= 0.9

    def test_workspace_routing(self):
        """Workspace questions route to WORKSPACE source."""
        questions = [
            "What project are we building?",
            "What phase are we on?",
            "What's the project type?",
            "What languages are we using?",
        ]
        for q in questions:
            decision = self.router.route(q)
            assert decision.source == TruthSource.WORKSPACE
            assert decision.confidence >= 0.8

    def test_git_routing(self):
        """Git questions route to GIT source."""
        questions = [
            "What's the current branch?",
            "Show git status",
            "What changed?",
            "Last commit?",
        ]
        for q in questions:
            decision = self.router.route(q)
            assert decision.source == TruthSource.GIT
            assert decision.confidence >= 0.8
            assert decision.needs_tools

    def test_system_routing(self):
        """System questions route to OBSERVERS source."""
        questions = [
            "Current RAM usage?",
            "How much disk space?",
            "CPU usage?",
            "Battery percent?",
        ]
        for q in questions:
            decision = self.router.route(q)
            assert decision.source == TruthSource.OBSERVERS
            assert decision.confidence >= 0.9

    def test_filesystem_routing(self):
        """Filesystem questions route to FILESYSTEM source."""
        questions = [
            "Where is MemoryManager?",
            "Find the planner module",
            "Search for test files",
        ]
        for q in questions:
            decision = self.router.route(q)
            assert decision.source == TruthSource.FILESYSTEM
            assert decision.needs_tools

    def test_llm_routing(self):
        """Pure knowledge questions route to LLM."""
        questions = [
            "Explain Rust ownership",
            "What is dependency injection?",
            "How does async/await work?",
        ]
        for q in questions:
            decision = self.router.route(q)
            assert decision.source == TruthSource.LLM

    def test_hybrid_routing(self):
        """Hybrid questions need both grounded data and LLM."""
        questions = [
            "Summarize the README",
            "Explain what this file does",
        ]
        for q in questions:
            decision = self.router.route(q)
            assert decision.source in {TruthSource.HYBRID, TruthSource.FILESYSTEM}

    def test_bypass_planner(self):
        """Fast path sources should bypass planner."""
        assert self.router.should_bypass_planner(TruthSource.MEMORY)
        assert self.router.should_bypass_planner(TruthSource.WORKSPACE)
        assert self.router.should_bypass_planner(TruthSource.OBSERVERS)
        assert not self.router.should_bypass_planner(TruthSource.FILESYSTEM)
        assert not self.router.should_bypass_planner(TruthSource.LLM)


class TestEvidence:
    """Test evidence collection."""

    def test_evidence_creation(self):
        """Evidence can be created and formatted."""
        evidence = Evidence(
            source=EvidenceSource.MEMORY,
            key="user_name",
            value="Alice",
            confidence=0.95,
        )
        assert evidence.source == EvidenceSource.MEMORY
        assert evidence.key == "user_name"
        assert evidence.value == "Alice"
        assert "user_name: Alice" in evidence.to_prompt_line()

    def test_evidence_bundle(self):
        """Evidence bundle can collect and group evidence."""
        bundle = EvidenceBundle()
        bundle.add(EvidenceSource.MEMORY, "name", "Alice")
        bundle.add(EvidenceSource.WORKSPACE, "project", "Friday")
        bundle.add(EvidenceSource.GIT, "branch", "main")

        assert len(bundle.items) == 3
        assert len(bundle.get_by_source(EvidenceSource.MEMORY)) == 1
        assert len(bundle.get_by_source(EvidenceSource.WORKSPACE)) == 1

        prompt = bundle.to_prompt_section()
        assert "EVIDENCE" in prompt
        assert "Memory:" in prompt
        assert "Workspace:" in prompt
        assert "Git:" in prompt

    def test_workspace_evidence(self):
        """Collect evidence from workspace state."""
        from core.world import DeveloperState, RuntimeState, ProcessState

        workspace = WorkspaceState(
            cwd="/test",
            project_type="python",
            languages=["python"],
            package_manager="pip",
            is_git_repo=True,
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
            name="TestProject",
            purpose="Test purpose",
            active_phase="Phase 9",
        )

        bundle = collect_workspace_evidence(world, project)
        assert not bundle.is_empty()

        workspace_items = bundle.get_by_source(EvidenceSource.WORKSPACE)
        keys = [item.key for item in workspace_items]
        assert "project_name" in keys
        assert "current_phase" in keys

    def test_git_evidence(self):
        """Collect evidence from git state."""
        from core.world import DeveloperState, RuntimeState, ProcessState

        workspace = WorkspaceState(
            cwd="/test",
            is_git_repo=True,
            git_branch="main",
            git_clean=True,
            git_modified_files=[],
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

        bundle = collect_git_evidence(world)
        assert not bundle.is_empty()

        git_items = bundle.get_by_source(EvidenceSource.GIT)
        keys = [item.key for item in git_items]
        assert "branch" in keys
        assert "status" in keys

    def test_system_evidence(self):
        """Collect evidence from system observers."""
        from core.world import DeveloperState, RuntimeState, ProcessState

        computer = ComputerState(
            os="Linux",
            ram_gb=16,
            logical_cores=8,
            disk_use_percent="45%",
            battery_percent="80%",
        )
        network = NetworkState(internet_reachable=True)
        world = WorldState(
            workspace=WorkspaceState(cwd="/test"),
            computer=computer,
            network=network,
            developer=DeveloperState(),
            runtime=RuntimeState(),
            processes=ProcessState(),
            observed_at=datetime.now(),
        )

        bundle = collect_system_evidence(world)
        assert not bundle.is_empty()

        observer_items = bundle.get_by_source(EvidenceSource.OBSERVERS)
        keys = [item.key for item in observer_items]
        assert "ram_gb" in keys
        assert "cpu_cores" in keys
        assert "os" in keys


class TestProjectContext:
    """Test project context inference."""

    def test_project_name_from_directory(self):
        """Infer project name from directory."""
        name = ProjectContext._infer_project_name("/home/user/MyProject")
        assert name == "MyProject"

    def test_project_context_creation(self):
        """Create project context from workspace state."""
        workspace = WorkspaceState(
            cwd="/test/Friday",
            project_type="python",
            languages=["python"],
            package_manager="pip",
        )

        context = ProjectContext.from_workspace(workspace, "/test/Friday")
        assert context.name == "Friday"
        assert context.project_type == "python"
        assert "python" in context.languages

    def test_project_context_to_prompt(self):
        """Format project context as prompt string."""
        context = ProjectContext(
            name="Friday",
            purpose="Agentic operating system",
            active_phase="Phase 9",
            project_type="python",
            languages=["python"],
            major_components=["core", "agents", "memory"],
        )

        prompt = context.to_prompt_context()
        assert "Project: Friday" in prompt
        assert "Phase 9" in prompt
        assert "python" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
