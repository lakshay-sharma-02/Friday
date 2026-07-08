"""Truth Router - determines the authoritative source for answering questions.

Phase 9: Reality-first architecture. The LLM synthesizes evidence, it does not invent it.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
import re


class TruthSource(Enum):
    """Authoritative sources of truth."""
    MEMORY = "memory"
    WORKSPACE = "workspace"
    WORLD = "world"
    GIT = "git"
    FILESYSTEM = "filesystem"
    OBSERVERS = "observers"
    LLM = "llm"
    HYBRID = "hybrid"


@dataclass
class RoutingDecision:
    """Result of truth routing."""
    source: TruthSource
    confidence: float
    needs_tools: bool = False
    tool_hints: list[str] = None

    def __post_init__(self):
        if self.tool_hints is None:
            self.tool_hints = []


class TruthRouter:
    """Routes questions to their authoritative source of truth.

    Never executes tools or plans. Only decides WHERE truth lives.
    """

    # Memory-related patterns
    MEMORY_PATTERNS = [
        r'\bmy name\b',
        r'\bwho am i\b',
        r'\bwhat did i (say|tell|teach)\b',
        r'\bdo you remember\b',
        r'\bwhat have i (taught|told)\b',
        r'\bmy preference\b',
        r'\bi (prefer|like|use)\b',
    ]

    # Project/workspace patterns
    PROJECT_PATTERNS = [
        r'\bwhat project\b',
        r'\bcurrent project\b',
        r'\bproject name\b',
        r'\bwhat are we building\b',
        r'\bwhat phase\b',
        r'\bcurrent phase\b',
        r'\bproject type\b',
        r'\blanguages?\b.*\busing\b',
        r'\bbuild system\b',
        r'\bpackage manager\b',
    ]

    # Git patterns
    GIT_PATTERNS = [
        r'\bgit\s+(branch|status|diff|log|commit)\b',
        r'\bcurrent branch\b',
        r'\blast commit\b',
        r'\bgit.*clean\b',
        r'\bgit.*dirty\b',
        r'\bmodified files?\b',
        r'\bwhat.*changed\b',
        r'\buncommitted\b',
    ]

    # System/world state patterns
    WORLD_PATTERNS = [
        r'\b(ram|memory|cpu|disk|battery)\b.*\b(usage|percent|available)\b',
        r'\bcurrent (ram|memory|cpu|disk|battery)\b',
        r'\bsystem (resources?|health)\b',
        r'\bhow much (ram|memory|disk)\b',
        r'\binternet (connection|reachable)\b',
        r'\bnetwork status\b',
    ]

    # Filesystem patterns
    FILESYSTEM_PATTERNS = [
        r'\bwhere is\b',
        r'\bfind (file|class|function|module|planner|the)\b',
        r'\bsearch for\b',
        r'\blist (files?|director(y|ies))\b',
        r'\bread\b.*\bfile\b',
        r'\bshow me\b.*\bfile\b',
        r'\blocate\b',
    ]

    # Pure LLM patterns (conceptual knowledge)
    LLM_PATTERNS = [
        r'\bexplain\b.*\b(concept|pattern|algorithm|theory)\b',
        r'\bwhat is\b.*\b(rust|python|java|javascript|go)\b',
        r'\bhow does\b.*\bwork\b',
        r'\bwhy (is|does|should)\b',
        r'\bcompare\b.*\band\b',
        r'\b(advantages?|disadvantages?|pros?|cons?)\b',
    ]

    def route(self, question: str) -> RoutingDecision:
        """Determine the authoritative source for this question.

        Returns where the truth lives, NOT how to answer it.
        """
        q_lower = question.lower().strip()

        # Memory first - personal facts and teachings
        if self._matches_patterns(q_lower, self.MEMORY_PATTERNS):
            return RoutingDecision(
                source=TruthSource.MEMORY,
                confidence=0.95,
                needs_tools=False
            )

        # Git state
        if self._matches_patterns(q_lower, self.GIT_PATTERNS):
            return RoutingDecision(
                source=TruthSource.GIT,
                confidence=0.9,
                needs_tools=True,
                tool_hints=["git_status", "git_diff", "git_log"]
            )

        # Project/workspace context
        if self._matches_patterns(q_lower, self.PROJECT_PATTERNS):
            return RoutingDecision(
                source=TruthSource.WORKSPACE,
                confidence=0.9,
                needs_tools=False
            )

        # System state (CPU, RAM, battery, etc.)
        if self._matches_patterns(q_lower, self.WORLD_PATTERNS):
            return RoutingDecision(
                source=TruthSource.OBSERVERS,
                confidence=0.95,
                needs_tools=False
            )

        # Filesystem queries
        if self._matches_patterns(q_lower, self.FILESYSTEM_PATTERNS):
            return RoutingDecision(
                source=TruthSource.FILESYSTEM,
                confidence=0.85,
                needs_tools=True,
                tool_hints=["search_files", "list_directory", "read_file"]
            )

        # Hybrid: needs both grounded data and LLM synthesis
        if any(word in q_lower for word in ["summarize", "explain", "what does"]) and \
           any(word in q_lower for word in ["file", "code", "readme", "this"]):
            return RoutingDecision(
                source=TruthSource.HYBRID,
                confidence=0.8,
                needs_tools=True,
                tool_hints=["read_file"]
            )

        # Pure conceptual knowledge - LLM last resort
        if self._matches_patterns(q_lower, self.LLM_PATTERNS):
            return RoutingDecision(
                source=TruthSource.LLM,
                confidence=0.7,
                needs_tools=False
            )

        # Default: assume LLM can handle it
        return RoutingDecision(
            source=TruthSource.LLM,
            confidence=0.5,
            needs_tools=False
        )

    def _matches_patterns(self, text: str, patterns: list[str]) -> bool:
        """Check if text matches any pattern in the list."""
        return any(re.search(pattern, text) for pattern in patterns)

    def should_bypass_planner(self, source: TruthSource) -> bool:
        """Determine if this source can answer without invoking the planner.

        Fast paths for grounded queries that don't need planning.
        """
        return source in {
            TruthSource.MEMORY,
            TruthSource.WORKSPACE,
            TruthSource.OBSERVERS,
        }
