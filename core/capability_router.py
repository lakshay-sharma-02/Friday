"""Capability Router - metadata-driven routing to authoritative sources.

Phase 10: Routes queries to capabilities based on semantic matching and metadata reasoning.
No hardcoded patterns - the router reasons over capability metadata.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from core.capability_registry import (
    get_capability_registry,
    CapabilityMetadata,
    CapabilityCategory,
    LatencyCategory
)


@dataclass
class CapabilityRoutingDecision:
    """Result of capability routing."""
    capability: CapabilityMetadata
    confidence: float
    reasoning: str  # Why this capability was chosen


class CapabilityRouter:
    """Routes queries to capabilities based on metadata reasoning.

    Never executes work. Only determines which capability owns the query.
    """

    def __init__(self):
        self.registry = get_capability_registry()

    def route(self, query: str) -> CapabilityRoutingDecision:
        """Route a query to the most appropriate capability.

        Reasoning process:
        1. Find capabilities matching keywords/synonyms
        2. Score by semantic relevance
        3. Prefer instant/fast capabilities over slow ones
        4. Return highest confidence match

        Args:
            query: Natural language query

        Returns:
            CapabilityRoutingDecision with capability and reasoning
        """
        query_lower = query.lower()

        # Step 1: Find candidates by keyword matching
        candidates = self.registry.find_by_keywords(query)

        if not candidates:
            # No keyword match - fall back to conceptual knowledge
            llm_capability = self.registry.get("conceptual_knowledge")
            return CapabilityRoutingDecision(
                capability=llm_capability,
                confidence=0.5,
                reasoning="No specific capability matched - falling back to LLM knowledge"
            )

        # Step 2: Score candidates
        scored = []
        for cap in candidates:
            score = self._score_capability(query_lower, cap)
            scored.append((score, cap))

        # Sort by score (highest first)
        scored.sort(reverse=True, key=lambda x: x[0])

        best_score, best_capability = scored[0]

        # Build reasoning
        reasoning = self._build_reasoning(query_lower, best_capability, best_score)

        return CapabilityRoutingDecision(
            capability=best_capability,
            confidence=best_score,
            reasoning=reasoning
        )

    def _score_capability(self, query: str, capability: CapabilityMetadata) -> float:
        """Score how well a capability matches the query.

        Scoring factors:
        - Keyword match strength (0.4)
        - Category relevance (0.2)
        - Latency preference (0.2) - prefer instant/fast
        - Complexity preference (0.2) - prefer simple over complex
        """
        score = 0.0

        # Keyword match strength (0.4)
        keyword_score = self._keyword_match_score(query, capability)
        score += keyword_score * 0.4

        # Category relevance (0.2)
        category_score = self._category_relevance(query, capability.category)
        score += category_score * 0.2

        # Latency preference (0.2) - instant > fast > moderate > slow
        latency_score = {
            LatencyCategory.INSTANT: 1.0,
            LatencyCategory.FAST: 0.8,
            LatencyCategory.MODERATE: 0.5,
            LatencyCategory.SLOW: 0.3
        }.get(capability.latency, 0.3)
        score += latency_score * 0.2

        # Complexity preference (0.2) - simpler is better
        complexity_score = 1.0
        if capability.requires_planner:
            complexity_score -= 0.3
        if capability.requires_executor:
            complexity_score -= 0.2
        if capability.requires_llm:
            complexity_score -= 0.1
        complexity_score = max(0, complexity_score)
        score += complexity_score * 0.2

        return score

    def _keyword_match_score(self, query: str, capability: CapabilityMetadata) -> float:
        """Score keyword matching strength."""
        matches = 0
        total_keywords = len(capability.keywords) + len(capability.synonyms)

        if total_keywords == 0:
            return 0.0

        # Check keywords
        for keyword in capability.keywords:
            if keyword in query:
                matches += 1

        # Check synonyms
        for synonym in capability.synonyms:
            if synonym in query:
                matches += 1

        return min(1.0, matches / max(1, total_keywords * 0.5))

    def _category_relevance(self, query: str, category: CapabilityCategory) -> float:
        """Score category relevance to query."""
        # Question words suggest different categories
        if any(q in query for q in ["what", "which", "current", "show"]):
            # Information queries
            if category in {CapabilityCategory.SYSTEM_STATE, CapabilityCategory.WORKSPACE,
                           CapabilityCategory.GIT, CapabilityCategory.MEMORY}:
                return 1.0
            return 0.6

        if any(q in query for q in ["where", "find", "search", "locate"]):
            # Search queries
            if category == CapabilityCategory.FILESYSTEM:
                return 1.0
            return 0.5

        if any(q in query for q in ["explain", "how", "why"]):
            # Knowledge queries
            if category == CapabilityCategory.KNOWLEDGE:
                return 1.0
            return 0.4

        if any(q in query for q in ["create", "write", "modify", "install", "setup"]):
            # Execution queries
            if category in {CapabilityCategory.EXECUTION, CapabilityCategory.FILESYSTEM}:
                return 1.0
            return 0.5

        return 0.7

    def _build_reasoning(self, query: str, capability: CapabilityMetadata, score: float) -> str:
        """Build human-readable reasoning for the routing decision."""
        parts = [f"Capability: {capability.name}"]

        # Explain why
        if capability.latency == LatencyCategory.INSTANT:
            parts.append("instant answer from in-memory state")
        elif capability.latency == LatencyCategory.FAST:
            parts.append("fast lookup")
        elif capability.requires_planner:
            parts.append("requires planning multi-step execution")
        elif capability.requires_executor:
            parts.append("requires tool execution")

        # Owner
        parts.append(f"owner: {capability.owner_module}")

        # Source
        parts.append(f"source: {capability.authoritative_source}")

        return " | ".join(parts)

    def get_execution_strategy(self, capability: CapabilityMetadata) -> dict:
        """Determine execution strategy for a capability.

        Returns a dict describing how to execute this capability.
        """
        strategy = {
            "capability": capability.name,
            "owner": capability.owner_module,
            "requires_planner": capability.requires_planner,
            "requires_executor": capability.requires_executor,
            "requires_llm": capability.requires_llm,
            "tools": capability.requires_tools,
            "latency": capability.latency.value,
            "produces_evidence": capability.produces_evidence
        }

        # Determine execution path
        if not capability.requires_planner and not capability.requires_executor:
            strategy["execution_path"] = "direct"
            strategy["explanation"] = "Answer directly from system state"
        elif capability.requires_executor and not capability.requires_planner:
            strategy["execution_path"] = "tool_direct"
            strategy["explanation"] = "Execute tool directly without planning"
        elif capability.requires_planner:
            strategy["execution_path"] = "pipeline"
            strategy["explanation"] = "Full pipeline: plan → validate → execute"
        else:
            strategy["execution_path"] = "llm"
            strategy["explanation"] = "LLM synthesis only"

        return strategy


def route_to_capability(query: str) -> Tuple[CapabilityMetadata, dict]:
    """Convenience function: route query and get execution strategy.

    Returns:
        Tuple of (capability, execution_strategy)
    """
    router = CapabilityRouter()
    decision = router.route(query)
    strategy = router.get_execution_strategy(decision.capability)

    return decision.capability, strategy
