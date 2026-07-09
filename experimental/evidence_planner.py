"""Evidence Planner - deterministic mapping from queries to required evidence.

EXPERIMENT ONLY - Can be removed if experiment fails.

NOT an LLM. NOT general NLP. Just pattern matching for known dogfooding cases.
"""

from dataclasses import dataclass
from typing import List, Optional
from experimental.evidence_types import EvidenceType


@dataclass
class EvidencePlan:
    """Plan for what evidence is needed to answer a query."""
    required_evidence: List[EvidenceType]
    confidence: float
    reasoning: str


class EvidencePlanner:
    """Maps natural language queries to required evidence types.

    Supports ONLY the dogfooding cases already observed:
    - "My name" → USER_PROFILE
    - "Current RAM" → SYSTEM_STATE
    - "Analyze this repository" → REPOSITORY + PROJECT_METADATA
    - "Install requests" → USER_PREFERENCES + PROJECT_METADATA
    - "What project" → PROJECT_METADATA + WORKSPACE
    - "Current branch" → GIT

    This is NOT general NLP. Just deterministic pattern matching.
    """

    def plan(self, query: str) -> Optional[EvidencePlan]:
        """Determine what evidence is needed for a query.

        Returns None if confidence is too low (should fallback to capability router).
        """
        query_lower = query.lower()

        # User identity queries
        if self._matches_user_identity(query_lower):
            return EvidencePlan(
                required_evidence=[EvidenceType.USER_PROFILE],
                confidence=0.95,
                reasoning="User identity query → USER_PROFILE"
            )

        # User preference queries
        if self._matches_user_preferences(query_lower):
            return EvidencePlan(
                required_evidence=[EvidenceType.USER_PREFERENCES, EvidenceType.PROJECT_METADATA],
                confidence=0.90,
                reasoning="User preference query (e.g., install method) → USER_PREFERENCES + PROJECT_METADATA"
            )

        # System state queries
        if self._matches_system_state(query_lower):
            return EvidencePlan(
                required_evidence=[EvidenceType.SYSTEM_STATE],
                confidence=0.95,
                reasoning="System state query → SYSTEM_STATE"
            )

        # Workspace/project queries
        if self._matches_workspace(query_lower):
            return EvidencePlan(
                required_evidence=[EvidenceType.WORKSPACE, EvidenceType.PROJECT_METADATA],
                confidence=0.90,
                reasoning="Workspace/project query → WORKSPACE + PROJECT_METADATA"
            )

        # Git queries
        if self._matches_git(query_lower):
            return EvidencePlan(
                required_evidence=[EvidenceType.GIT],
                confidence=0.95,
                reasoning="Git query → GIT"
            )

        # Repository analysis queries
        if self._matches_repository_analysis(query_lower):
            return EvidencePlan(
                required_evidence=[
                    EvidenceType.REPOSITORY,
                    EvidenceType.PROJECT_METADATA,
                    EvidenceType.ARCHITECTURE
                ],
                confidence=0.85,
                reasoning="Repository analysis query → REPOSITORY + PROJECT_METADATA + ARCHITECTURE"
            )

        # Low confidence - should fallback
        return None

    def _matches_user_identity(self, query: str) -> bool:
        """Match user identity queries."""
        patterns = [
            "my name",
            "my full name",
            "what is my name",
            "what's my name",
            "who am i",
            "who is the user",
        ]
        return any(pattern in query for pattern in patterns)

    def _matches_user_preferences(self, query: str) -> bool:
        """Match user preference queries."""
        # Installation preference patterns
        install_patterns = [
            "how should i install",
            "how should we install",
            "how do i install",
            "how would you install",
            "what command installs",
            "install command for",
            "how to add",
            "how do i add",
        ]

        # Other preference patterns
        preference_patterns = [
            "what do i prefer",
            "what do i usually",
            "my preference",
            "my preferred",
            "what have i told you",
            "what did i teach",
        ]

        return (any(pattern in query for pattern in install_patterns) or
                any(pattern in query for pattern in preference_patterns))

    def _matches_system_state(self, query: str) -> bool:
        """Match system state queries."""
        patterns = [
            "current ram",
            "ram usage",
            "available memory",
            "how much ram",
            "cpu cores",
            "how many cores",
            "battery level",
            "battery percent",
            "disk space",
            "disk usage",
            "internet",
            "network",
        ]
        return any(pattern in query for pattern in patterns)

    def _matches_workspace(self, query: str) -> bool:
        """Match workspace/project queries."""
        patterns = [
            "what project",
            "which project",
            "current project",
            "project name",
            "what repo",
            "which repo",
            "what workspace",
            "current workspace",
            "working directory",
            "this project",
            "this repo",
            "this codebase",
        ]
        return any(pattern in query for pattern in patterns)

    def _matches_git(self, query: str) -> bool:
        """Match git queries."""
        patterns = [
            "current branch",
            "git branch",
            "what branch",
            "which branch",
            "git status",
            "git clean",
            "uncommitted",
        ]
        return any(pattern in query for pattern in patterns)

    def _matches_repository_analysis(self, query: str) -> bool:
        """Match repository analysis queries."""
        analysis_verbs = ["analyze", "review", "summarize", "describe", "explain"]
        targets = ["repository", "repo", "codebase", "project", "code"]

        # Check if query contains an analysis verb + target
        has_verb = any(verb in query for verb in analysis_verbs)
        has_target = any(target in query for target in targets)

        # Also check for "this repo", "this project", etc. with analysis intent
        if has_verb and ("this " in query or "the " in query):
            has_target = True

        return has_verb and has_target
