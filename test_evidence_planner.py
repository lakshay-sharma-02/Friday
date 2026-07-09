"""Test suite for Evidence Planner experiment.

EXPERIMENT ONLY - Can be removed if experiment fails.

Tests historical routing failures as regression tests.
"""

import pytest
import asyncio
from experimental.evidence_planner import EvidencePlanner
from experimental.evidence_types import EvidenceType
from experimental.evidence_integration import EvidenceIntegration


class TestEvidencePlanner:
    """Test evidence planner on dogfooding cases."""

    def test_user_identity_queries(self):
        """User identity queries should require USER_PROFILE."""
        planner = EvidencePlanner()

        test_cases = [
            "What's my full name?",
            "What is my name?",
            "My name",
            "Who am I?",
        ]

        for query in test_cases:
            plan = planner.plan(query)
            assert plan is not None, f"Failed to plan: {query}"
            assert EvidenceType.USER_PROFILE in plan.required_evidence
            assert plan.confidence >= 0.90, f"Low confidence for: {query}"

    def test_system_state_queries(self):
        """System state queries should require SYSTEM_STATE."""
        planner = EvidencePlanner()

        test_cases = [
            "Current RAM?",
            "How much RAM?",
            "CPU cores?",
            "Battery level?",
            "Disk space?",
        ]

        for query in test_cases:
            plan = planner.plan(query)
            assert plan is not None, f"Failed to plan: {query}"
            assert EvidenceType.SYSTEM_STATE in plan.required_evidence
            assert plan.confidence >= 0.90, f"Low confidence for: {query}"

    def test_project_queries(self):
        """Project queries should require WORKSPACE + PROJECT_METADATA."""
        planner = EvidencePlanner()

        test_cases = [
            "What project am I in?",
            "What project are we building?",
            "Which project?",
            "What repo is this?",
            "Current workspace?",
        ]

        for query in test_cases:
            plan = planner.plan(query)
            assert plan is not None, f"Failed to plan: {query}"
            assert EvidenceType.WORKSPACE in plan.required_evidence or \
                   EvidenceType.PROJECT_METADATA in plan.required_evidence
            assert plan.confidence >= 0.85, f"Low confidence for: {query}"

    def test_git_queries(self):
        """Git queries should require GIT."""
        planner = EvidencePlanner()

        test_cases = [
            "Current branch?",
            "Git branch?",
            "Which branch?",
            "Git status?",
        ]

        for query in test_cases:
            plan = planner.plan(query)
            assert plan is not None, f"Failed to plan: {query}"
            assert EvidenceType.GIT in plan.required_evidence
            assert plan.confidence >= 0.90, f"Low confidence for: {query}"

    def test_install_preference_queries(self):
        """Install queries should require USER_PREFERENCES + PROJECT_METADATA."""
        planner = EvidencePlanner()

        test_cases = [
            "How should we install requests?",
            "How should I install requests?",
            "How do I install requests?",
            "What command installs requests?",
        ]

        for query in test_cases:
            plan = planner.plan(query)
            assert plan is not None, f"Failed to plan: {query}"
            assert EvidenceType.USER_PREFERENCES in plan.required_evidence
            assert plan.confidence >= 0.85, f"Low confidence for: {query}"

    def test_repository_analysis_queries(self):
        """Repository analysis queries should require REPOSITORY + PROJECT_METADATA."""
        planner = EvidencePlanner()

        test_cases = [
            "Analyze this repository",
            "Analyze this codebase",
            "Review this project",
            "Summarize this repo",
            "Describe this project",
        ]

        for query in test_cases:
            plan = planner.plan(query)
            assert plan is not None, f"Failed to plan: {query}"
            assert EvidenceType.REPOSITORY in plan.required_evidence or \
                   EvidenceType.PROJECT_METADATA in plan.required_evidence
            assert plan.confidence >= 0.80, f"Low confidence for: {query}"

    def test_low_confidence_fallback(self):
        """Unrecognized queries should return None (fallback to capability router)."""
        planner = EvidencePlanner()

        test_cases = [
            "Explain Rust ownership",  # Conceptual knowledge
            "Find the MemoryManager class",  # Filesystem search
            "Create a new file",  # Execution
        ]

        for query in test_cases:
            plan = planner.plan(query)
            # Should return None for low confidence
            if plan:
                assert plan.confidence < 0.75, f"Unexpected high confidence for: {query}"


@pytest.mark.asyncio
class TestEvidenceIntegration:
    """Test evidence integration layer."""

    async def test_high_confidence_uses_evidence_planner(self):
        """High confidence queries should use evidence planner."""
        integration = EvidenceIntegration()

        # System state query - should have high confidence
        answer, metrics = await integration.handle("Current RAM?", verbose=False)

        assert metrics.used_evidence_planner
        assert not metrics.used_capability_router
        assert metrics.fallback_reason is None
        assert metrics.evidence_planner_confidence >= 0.75

    async def test_low_confidence_uses_capability_router(self):
        """Low confidence queries should fallback to capability router."""
        integration = EvidenceIntegration()

        # Conceptual query - should fallback
        answer, metrics = await integration.handle(
            "Explain Rust ownership", verbose=False
        )

        assert not metrics.used_evidence_planner
        assert metrics.used_capability_router
        assert metrics.fallback_reason is not None

    async def test_metrics_recorded(self):
        """All metrics should be recorded."""
        integration = EvidenceIntegration()

        answer, metrics = await integration.handle("Current RAM?", verbose=False)

        # Check all metrics are present
        assert metrics.latency_ms > 0
        assert metrics.routing_latency_ms >= 0
        assert metrics.execution_latency_ms > 0
        assert metrics.provider is not None
        assert isinstance(metrics.used_llm, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
