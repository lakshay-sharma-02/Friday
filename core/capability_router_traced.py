"""Traced capability router - adds tracing to routing decisions."""

from core.capability_router import CapabilityRouter, CapabilityRoutingDecision
from core.trace import get_current_trace, TraceStage


class TracedCapabilityRouter(CapabilityRouter):
    """Capability router with request tracing."""

    def route(self, query: str) -> CapabilityRoutingDecision:
        """Route with tracing."""
        trace = get_current_trace()

        if trace:
            trace.start_stage(TraceStage.CAPABILITY_ROUTING, input_data={
                "query": query
            })

        try:
            decision = super().route(query)

            if trace:
                # Record routing decision
                trace.set_routing(
                    capability=decision.capability.name,
                    operation=decision.operation.value,
                    confidence=decision.confidence,
                    intent=query
                )

                trace.end_stage(output_data={
                    "capability": decision.capability.name,
                    "operation": decision.operation.value,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning
                })

            return decision

        except Exception as e:
            if trace:
                trace.end_stage(errors=[str(e)])
            raise


def get_capability_router():
    """Get appropriate router based on tracing state."""
    from core.trace_wrapper import is_tracing_enabled

    if is_tracing_enabled():
        return TracedCapabilityRouter()
    else:
        return CapabilityRouter()
