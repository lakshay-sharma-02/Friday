"""Evidence Executor - collects evidence and synthesizes answers.

EXPERIMENT ONLY - Can be removed if experiment fails.
"""

from dataclasses import dataclass
from typing import List, Tuple
import time

from experimental.evidence_types import EvidenceType
from experimental.evidence_providers import (
    Evidence,
    MemoryProvider,
    SystemProvider,
    WorkspaceProvider,
    GitProvider,
    RepositoryProvider,
)


@dataclass
class EvidenceExecutionResult:
    """Result of evidence collection and synthesis."""
    answer: str
    evidence_collected: List[Evidence]
    latency_ms: float
    source: str
    used_llm: bool = False


class EvidenceExecutor:
    """Executes evidence collection and synthesis.

    Collects evidence from providers, then synthesizes an answer.
    """

    def __init__(self):
        # Initialize providers
        self.providers = [
            MemoryProvider(),
            SystemProvider(),
            WorkspaceProvider(),
            GitProvider(),
            RepositoryProvider(),
        ]

    async def execute(
        self, query: str, required_evidence: List[EvidenceType]
    ) -> EvidenceExecutionResult:
        """Execute evidence collection and synthesis.

        Args:
            query: Original user query
            required_evidence: List of evidence types needed

        Returns:
            EvidenceExecutionResult with answer and metadata
        """
        t_start = time.perf_counter()

        # Step 1: Collect evidence from all providers
        all_evidence = []
        for provider in self.providers:
            evidence = await provider.collect(query, required_evidence)
            all_evidence.extend(evidence)

        # Step 2: Synthesize answer from evidence
        if not all_evidence:
            # No evidence collected - fallback to LLM
            from core.model_client import call_model
            answer = await call_model(query, enable_thinking=False)
            latency_ms = (time.perf_counter() - t_start) * 1000
            return EvidenceExecutionResult(
                answer=answer,
                evidence_collected=[],
                latency_ms=latency_ms,
                source="LLM (no evidence)",
                used_llm=True
            )

        # Build synthesis prompt
        answer = await self._synthesize_from_evidence(query, all_evidence)

        latency_ms = (time.perf_counter() - t_start) * 1000

        sources = set(e.source for e in all_evidence)
        return EvidenceExecutionResult(
            answer=answer,
            evidence_collected=all_evidence,
            latency_ms=latency_ms,
            source=f"Evidence ({', '.join(sources)})",
            used_llm=True
        )

    async def _synthesize_from_evidence(
        self, query: str, evidence: List[Evidence]
    ) -> str:
        """Synthesize answer from collected evidence using LLM.

        Args:
            query: Original user query
            evidence: List of evidence items

        Returns:
            Synthesized answer string
        """
        from core.model_client import call_model

        # Build prompt with evidence
        prompt_parts = []
        prompt_parts.append("You are answering a query using collected evidence.")
        prompt_parts.append("The evidence below is AUTHORITATIVE - use it directly.")
        prompt_parts.append("")

        # Group evidence by type
        evidence_by_type = {}
        for item in evidence:
            if item.type not in evidence_by_type:
                evidence_by_type[item.type] = []
            evidence_by_type[item.type].append(item)

        # Format evidence by type
        for evidence_type, items in evidence_by_type.items():
            prompt_parts.append(f"## {evidence_type.value.upper()}")
            for item in items:
                prompt_parts.append(f"Source: {item.source}")
                prompt_parts.append(f"Data: {item.data}")
                prompt_parts.append("")

        prompt_parts.append(f"User query: {query}")
        prompt_parts.append("")
        prompt_parts.append("Answer the query using ONLY the evidence above. "
                           "Be direct and concise.")

        prompt = "\n".join(prompt_parts)

        return await call_model(prompt, enable_thinking=False)
