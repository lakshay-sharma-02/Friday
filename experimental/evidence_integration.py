"""Evidence-based routing integration layer.

EXPERIMENT ONLY - Can be removed if experiment fails.

Integration point that tries Evidence Planner first, falls back to Capability Router.
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import time

from experimental.evidence_planner import EvidencePlanner
from experimental.evidence_executor import EvidenceExecutor
from core.capability_layer import CapabilityLayer


@dataclass
class RoutingMetrics:
    """Instrumentation for routing decisions."""
    # Routing decision
    used_evidence_planner: bool
    used_capability_router: bool
    fallback_reason: Optional[str]

    # Evidence planner metrics
    evidence_planner_confidence: Optional[float]
    evidence_types_requested: list
    evidence_items_collected: int

    # Performance
    latency_ms: float
    routing_latency_ms: float
    execution_latency_ms: float

    # Final result
    provider: str
    used_llm: bool


# Confidence threshold for Evidence Planner
CONFIDENCE_THRESHOLD = 0.75


class EvidenceIntegration:
    """Integration layer for experimental evidence-based routing.

    Flow:
        1. Try Evidence Planner
        2. If confidence >= threshold: collect evidence and synthesize
        3. Else: fallback to Capability Router

    All experimental code is isolated here. Can be removed by deleting this integration.
    """

    def __init__(self):
        self.evidence_planner = EvidencePlanner()
        self.evidence_executor = EvidenceExecutor()
        self.capability_layer = CapabilityLayer()

    async def handle(self, query: str, verbose: bool = False) -> Tuple[str, RoutingMetrics]:
        """Handle a query with evidence-based routing.

        Args:
            query: Natural language query
            verbose: If True, print routing decisions

        Returns:
            Tuple of (answer, metrics)
        """
        t_total_start = time.perf_counter()

        # Step 1: Try Evidence Planner
        t_routing_start = time.perf_counter()
        evidence_plan = self.evidence_planner.plan(query)
        t_routing = time.perf_counter() - t_routing_start

        if evidence_plan and evidence_plan.confidence >= CONFIDENCE_THRESHOLD:
            # High confidence - use Evidence Planner
            if verbose:
                print(f"[evidence] {evidence_plan.reasoning} (confidence: {evidence_plan.confidence:.2f})")

            # Execute evidence collection
            t_exec_start = time.perf_counter()
            result = await self.evidence_executor.execute(
                query, evidence_plan.required_evidence
            )
            t_exec = time.perf_counter() - t_exec_start

            t_total = time.perf_counter() - t_total_start

            metrics = RoutingMetrics(
                used_evidence_planner=True,
                used_capability_router=False,
                fallback_reason=None,
                evidence_planner_confidence=evidence_plan.confidence,
                evidence_types_requested=[et.value for et in evidence_plan.required_evidence],
                evidence_items_collected=len(result.evidence_collected),
                latency_ms=t_total * 1000,
                routing_latency_ms=t_routing * 1000,
                execution_latency_ms=t_exec * 1000,
                provider=result.source,
                used_llm=result.used_llm
            )

            return result.answer, metrics

        else:
            # Low confidence or no plan - fallback to Capability Router
            fallback_reason = (
                "no plan matched"
                if evidence_plan is None
                else f"confidence too low ({evidence_plan.confidence:.2f} < {CONFIDENCE_THRESHOLD})"
            )

            if verbose:
                print(f"[evidence] fallback to capability router: {fallback_reason}")

            # Execute through capability layer
            t_exec_start = time.perf_counter()
            answer, cap_metadata = await self.capability_layer.handle(query, verbose=verbose)
            t_exec = time.perf_counter() - t_exec_start

            t_total = time.perf_counter() - t_total_start

            metrics = RoutingMetrics(
                used_evidence_planner=False,
                used_capability_router=True,
                fallback_reason=fallback_reason,
                evidence_planner_confidence=evidence_plan.confidence if evidence_plan else None,
                evidence_types_requested=[],
                evidence_items_collected=0,
                latency_ms=t_total * 1000,
                routing_latency_ms=t_routing * 1000,
                execution_latency_ms=t_exec * 1000,
                provider=cap_metadata.get("source", "unknown"),
                used_llm=cap_metadata.get("used_llm", False)
            )

            return answer, metrics
