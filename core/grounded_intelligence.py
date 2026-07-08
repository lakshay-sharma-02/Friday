"""Grounded Intelligence - Reality-first question answering.

The LLM synthesizes evidence from authoritative sources.
It does not invent facts.
"""

import asyncio
from typing import Optional, Tuple
from core.truth_router import TruthRouter, TruthSource, RoutingDecision
from core.evidence import (
    EvidenceBundle,
    EvidenceSource,
    collect_memory_evidence,
    collect_workspace_evidence,
    collect_git_evidence,
    collect_system_evidence,
)
from core.project_context import ProjectContext
from core.world import WorldState
from memory.manager import MemoryManager


class GroundedIntelligence:
    """Answers questions using reality as the primary source of truth.

    The LLM is the LAST resort, not the first.
    """

    def __init__(self):
        self.router = TruthRouter()
        self.memory_manager = MemoryManager()

    async def answer(
        self,
        question: str,
        world: Optional[WorldState] = None,
        project_context: Optional[ProjectContext] = None,
    ) -> Tuple[str, RoutingDecision]:
        """Answer a question using grounded sources.

        Returns:
            Tuple of (answer string, routing decision used)
        """
        # Route to determine truth source
        decision = self.router.route(question)

        # Collect evidence based on routing
        evidence = await self._collect_evidence(
            question, decision, world, project_context
        )

        # If we have complete evidence and no tools needed, answer directly
        if not evidence.is_empty() and not decision.needs_tools:
            answer = self._answer_from_evidence(question, evidence, decision)
            return answer, decision

        # Otherwise, we need the LLM (either for synthesis or pure knowledge)
        answer = await self._answer_with_llm(question, evidence, decision)
        return answer, decision

    async def _collect_evidence(
        self,
        question: str,
        decision: RoutingDecision,
        world: Optional[WorldState],
        project_context: Optional[ProjectContext],
    ) -> EvidenceBundle:
        """Collect evidence from all relevant sources."""
        bundle = EvidenceBundle()

        # Collect based on routed source
        if decision.source == TruthSource.MEMORY:
            memory_bundle = await asyncio.to_thread(
                collect_memory_evidence, self.memory_manager, question
            )
            bundle.items.extend(memory_bundle.items)

        elif decision.source == TruthSource.WORKSPACE:
            if world and project_context:
                workspace_bundle = collect_workspace_evidence(world, project_context)
                bundle.items.extend(workspace_bundle.items)

        elif decision.source == TruthSource.GIT:
            if world:
                git_bundle = collect_git_evidence(world)
                bundle.items.extend(git_bundle.items)

        elif decision.source == TruthSource.OBSERVERS:
            if world:
                system_bundle = collect_system_evidence(world)
                bundle.items.extend(system_bundle.items)

        elif decision.source == TruthSource.HYBRID:
            # Collect from multiple sources for hybrid queries
            if world and project_context:
                workspace_bundle = collect_workspace_evidence(world, project_context)
                bundle.items.extend(workspace_bundle.items)

            memory_bundle = await asyncio.to_thread(
                collect_memory_evidence, self.memory_manager, question
            )
            bundle.items.extend(memory_bundle.items)

        return bundle

    def _answer_from_evidence(
        self, question: str, evidence: EvidenceBundle, decision: RoutingDecision
    ) -> str:
        """Answer directly from evidence without LLM when possible."""

        # Memory queries
        if decision.source == TruthSource.MEMORY:
            memory_items = evidence.get_by_source(EvidenceSource.MEMORY)
            if memory_items:
                # Format memory results
                lines = []
                for item in memory_items:
                    lines.append(f"- {item.value}")
                return "\n".join(lines)
            return "I don't have any relevant memories about that."

        # Workspace queries
        if decision.source == TruthSource.WORKSPACE:
            workspace_items = evidence.get_by_source(EvidenceSource.WORKSPACE)
            if workspace_items:
                lines = []
                for item in workspace_items:
                    lines.append(f"{item.key}: {item.value}")
                return "\n".join(lines)

        # Git queries
        if decision.source == TruthSource.GIT:
            git_items = evidence.get_by_source(EvidenceSource.GIT)
            if git_items:
                lines = []
                for item in git_items:
                    if isinstance(item.value, bool):
                        value = "yes" if item.value else "no"
                    else:
                        value = item.value
                    lines.append(f"{item.key}: {value}")
                return "\n".join(lines)

        # System/observer queries
        if decision.source == TruthSource.OBSERVERS:
            observer_items = evidence.get_by_source(EvidenceSource.OBSERVERS)
            if observer_items:
                lines = []
                for item in observer_items:
                    lines.append(f"{item.key}: {item.value}")
                return "\n".join(lines)

        # Default: couldn't answer from evidence alone
        return ""

    async def _answer_with_llm(
        self, question: str, evidence: EvidenceBundle, decision: RoutingDecision
    ) -> str:
        """Use LLM to synthesize answer, with evidence as context."""
        from core.model_client import call_model

        # Build prompt with evidence
        prompt_parts = []

        if not evidence.is_empty():
            evidence_section = evidence.to_prompt_section()
            prompt_parts.append(evidence_section)
            prompt_parts.append("\n---\n")
            prompt_parts.append(
                "Use ONLY the evidence above to answer. "
                "If the evidence doesn't contain the answer, say so explicitly. "
                "Do not invent facts."
            )
            prompt_parts.append(f"\nQuestion: {question}")
        else:
            # No evidence - pure LLM knowledge
            prompt_parts.append(f"Question: {question}")

        prompt = "\n".join(prompt_parts)

        # Call LLM for synthesis
        response = await call_model(prompt, enable_thinking=False)
        return response

    def get_routing_info(self, question: str) -> dict:
        """Get routing information for debugging/verbose mode."""
        decision = self.router.route(question)
        return {
            "source": decision.source.value,
            "confidence": decision.confidence,
            "needs_tools": decision.needs_tools,
            "tool_hints": decision.tool_hints,
            "bypass_planner": self.router.should_bypass_planner(decision.source),
        }
