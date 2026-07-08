"""Unified Capability Layer - Phase 10 integration point.

Combines Capability Router and Executor into a single unified interface.
This is the entry point for all capability-based queries.
"""

import asyncio
from typing import Tuple, Optional

from core.capability_router import CapabilityRouter, CapabilityRoutingDecision
from core.capability_executor import CapabilityExecutor, CapabilityResult, format_capability_result
from core.world import WorldState
from core.project_context import ProjectContext
from core.world_manager import observe_world
from core.world import RuntimeState


class CapabilityLayer:
    """Unified capability layer - the single entry point for capability routing and execution.

    Phase 10: Routes queries to capabilities and executes them using their owning subsystems.
    Never duplicates functionality - always delegates to existing subsystems.
    """

    def __init__(self):
        self.router = CapabilityRouter()
        self.executor = CapabilityExecutor()

    async def handle(self, query: str, verbose: bool = False) -> Tuple[str, dict]:
        """Handle a query through the capability layer.

        Args:
            query: Natural language query
            verbose: If True, include routing metadata in response

        Returns:
            Tuple of (answer string, metadata dict)
        """
        # Step 1: Route to capability
        decision = self.router.route(query)

        if verbose:
            print(f"[capability] {decision.reasoning}")

        # Step 2: Get execution strategy
        strategy = self.router.get_execution_strategy(decision.capability)

        # Step 3: Handle based on execution path
        if strategy["execution_path"] == "direct":
            # Direct answer from system state
            answer, metadata = await self._handle_direct(query, decision, strategy, verbose)

        elif strategy["execution_path"] == "tool_direct":
            # Tool execution without planning
            answer, metadata = await self._handle_tool_direct(query, decision, strategy, verbose)

        elif strategy["execution_path"] == "pipeline":
            # Full pipeline execution (requires planning)
            answer, metadata = await self._handle_pipeline(query, decision, strategy, verbose)

        elif strategy["execution_path"] == "llm":
            # Pure LLM knowledge
            answer, metadata = await self._handle_llm(query, decision, strategy, verbose)

        else:
            answer = f"Unknown execution path: {strategy['execution_path']}"
            metadata = {"error": "unknown_execution_path"}

        # Add capability metadata
        metadata["capability"] = decision.capability.name
        metadata["category"] = decision.capability.category.value
        metadata["confidence"] = decision.confidence

        return answer, metadata

    async def _handle_direct(
        self, query: str, decision: CapabilityRoutingDecision, strategy: dict, verbose: bool
    ) -> Tuple[str, dict]:
        """Handle direct queries (instant answers from system state)."""
        # Build world state and project context
        world = await observe_world(cwd=".", runtime=RuntimeState())
        project_context = ProjectContext.from_workspace(world.workspace, ".")

        # Execute capability
        result = await self.executor.execute(
            decision.capability, query, world, project_context
        )

        # Format answer
        answer = format_capability_result(result, decision.capability)

        metadata = {
            "execution_path": "direct",
            "latency_ms": result.latency_ms,
            "source": result.source,
            "used_llm": result.used_llm
        }

        return answer, metadata

    async def _handle_tool_direct(
        self, query: str, decision: CapabilityRoutingDecision, strategy: dict, verbose: bool
    ) -> Tuple[str, dict]:
        """Handle tool execution without planning.

        Note: Currently filesystem operations still require Pipeline.
        Future: Allow direct tool execution for safe read-only tools.
        """
        # For now, filesystem operations go through pipeline
        return await self._handle_pipeline(query, decision, strategy, verbose)

    async def _handle_pipeline(
        self, query: str, decision: CapabilityRoutingDecision, strategy: dict, verbose: bool
    ) -> Tuple[str, dict]:
        """Handle full pipeline execution (planning + execution).

        Delegates to existing Pipeline infrastructure.
        """
        from core.run import PipelineRun
        from core.intent import Intent
        from core.pipeline import run_pipeline

        # Create intent and run
        intent = Intent(kind="task", payload={"text": query})
        pipeline_run = PipelineRun(intent=intent)

        try:
            response = await run_pipeline(pipeline_run)
            metadata = {
                "execution_path": "pipeline",
                "status": pipeline_run.status,
                "steps": len(pipeline_run.execution_log)
            }
            return response, metadata

        except Exception as e:
            return f"Pipeline execution failed: {e}", {"error": str(e)}

    async def _handle_llm(
        self, query: str, decision: CapabilityRoutingDecision, strategy: dict, verbose: bool
    ) -> Tuple[str, dict]:
        """Handle pure LLM knowledge queries."""
        # Execute via capability executor (which calls LLM)
        result = await self.executor.execute(decision.capability, query)

        answer = format_capability_result(result, decision.capability)

        metadata = {
            "execution_path": "llm",
            "latency_ms": result.latency_ms,
            "source": result.source,
            "used_llm": True
        }

        return answer, metadata


# Convenience function
async def query_capability(query: str, verbose: bool = False) -> Tuple[str, dict]:
    """Convenience function to query through the capability layer."""
    layer = CapabilityLayer()
    return await layer.handle(query, verbose=verbose)
