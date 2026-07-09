"""Unified Capability Layer - Phase 10 integration point.

Combines Capability Router and Executor into a single unified interface.
This is the entry point for all capability-based queries.

Phase 10.5: Now understands operation semantics (WHAT user wants to do).
"""

import asyncio
from typing import Tuple, Optional

from core.capability_router import CapabilityRouter, CapabilityRoutingDecision
from core.capability_executor import CapabilityExecutor, CapabilityResult, format_capability_result
from core.world import WorldState
from core.project_context import ProjectContext
from core.world_manager import observe_world
from core.world import RuntimeState
from core.operations import Operation
from core.evidence import EvidenceBundle


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
        strategy = self.router.get_execution_strategy(decision.capability, decision.operation)

        # Step 3: Handle based on execution path
        if strategy["execution_path"] == "advise":
            # Phase 10.5: ADVISE path (never executes)
            answer, metadata = await self._handle_advise(query, decision, strategy, verbose)

        elif strategy["execution_path"] == "direct":
            # Direct answer from system state
            answer, metadata = await self._handle_direct(query, decision, strategy, verbose)

        elif strategy["execution_path"] == "synthesis":
            # Phase 10.5: Synthesis path (evidence + LLM)
            answer, metadata = await self._handle_synthesis(query, decision, strategy, verbose)

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
        metadata["operation"] = decision.operation.value  # Phase 10.5
        metadata["confidence"] = decision.confidence

        return answer, metadata

    async def _handle_advise(
        self, query: str, decision: CapabilityRoutingDecision, strategy: dict, verbose: bool
    ) -> Tuple[str, dict]:
        """Handle ADVISE operations (advice without execution).

        Phase 10.5: ADVISE operations NEVER execute tools or invoke planner.
        They consult memory for preferences, then LLM for synthesis.
        """
        from memory.manager import MemoryManager
        from core.model_client import call_model
        import time

        memory_manager = MemoryManager()

        t_start = time.perf_counter()

        # Step 1: Check memory for relevant preferences/teachings
        memory_results = []
        try:
            memory_results = await asyncio.to_thread(memory_manager.search, query, limit=3)
        except Exception:
            pass

        # Step 2: Build prompt with memory context
        prompt_parts = []

        prompt_parts.append(
            "Retrieved evidence (especially explicit teachings and remembered "
            "preferences) is AUTHORITATIVE and takes precedence over your own "
            "model priors. Never recommend something that contradicts a retrieved "
            "preference (e.g. if memory says 'use uv', do NOT suggest pip unless the "
            "user explicitly asks to ignore their preferences)."
        )
        prompt_parts.append("")

        if memory_results:
            prompt_parts.append("User's remembered preferences (highest priority):")
            for result in memory_results:
                content = result.get("content", result.get("text", ""))
                if content:
                    prompt_parts.append(f"- {content}")
            prompt_parts.append("")

        prompt_parts.append(f"User question: {query}")
        prompt_parts.append("")
        prompt_parts.append("Provide advice based on the user's preferences above. "
                           "Do NOT execute anything. Just recommend the best approach.")

        prompt = "\n".join(prompt_parts)

        # Step 3: LLM synthesis (no execution)
        response = await call_model(prompt, enable_thinking=False)

        latency_ms = (time.perf_counter() - t_start) * 1000

        metadata = {
            "execution_path": "advise",
            "operation": decision.operation.value,
            "latency_ms": latency_ms,
            "source": "Memory + LLM",
            "used_llm": True,
            "used_memory": len(memory_results) > 0,
            "executed_tools": False
        }

        return response, metadata

    async def _handle_direct(
        self, query: str, decision: CapabilityRoutingDecision, strategy: dict, verbose: bool
    ) -> Tuple[str, dict]:
        """Handle direct queries (instant answers from system state)."""
        from core.operations import Operation

        # Phase 10.5: ADVISE operation gets special handling
        if decision.operation == Operation.ADVISE:
            return await self._handle_advise(query, decision, strategy, verbose)

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
            "operation": decision.operation.value,
            "latency_ms": result.latency_ms,
            "source": result.source,
            "used_llm": result.used_llm
        }

        return answer, metadata

    async def _handle_synthesis(
        self, query: str, decision: CapabilityRoutingDecision, strategy: dict, verbose: bool
    ) -> Tuple[str, dict]:
        """Handle synthesis operations (evidence collection + LLM).

        Phase 10.5: EXPLAIN, SUMMARIZE, REVIEW, ANALYZE operations collect
        evidence from authoritative sources, then LLM synthesizes.
        """
        from core.model_client import call_model
        from core.evidence import (
            collect_workspace_evidence,
            collect_git_evidence,
            collect_system_evidence,
            collect_document_evidence,
            collect_memory_evidence,
            build_synthesis_prompt,
        )
        from memory.manager import MemoryManager
        from datetime import datetime
        import time

        t_start = time.perf_counter()

        # Collect evidence from authoritative sources BEFORE asking the LLM.
        from core.world import RuntimeState
        world = await observe_world(cwd=".", runtime=RuntimeState())
        project_context = ProjectContext.from_workspace(world.workspace, ".")

        bundle = EvidenceBundle()
        bundle.items.extend(collect_workspace_evidence(world, project_context).items)
        bundle.items.extend(collect_git_evidence(world).items)
        bundle.items.extend(collect_system_evidence(world).items)
        bundle.items.extend(collect_document_evidence(".").items)

        memory_manager = MemoryManager()
        try:
            mem_results = await asyncio.to_thread(memory_manager.search, query, limit=5)
        except Exception:
            mem_results = []
        bundle.items.extend(collect_memory_evidence(memory_manager, query).items)

        prompt = build_synthesis_prompt(bundle, query)

        response = await call_model(prompt, enable_thinking=False)

        latency_ms = (time.perf_counter() - t_start) * 1000

        metadata = {
            "execution_path": "synthesis",
            "operation": decision.operation.value,
            "latency_ms": latency_ms,
            "source": "Evidence + LLM synthesis",
            "used_llm": True,
            "evidence_sources": sorted({e.source.value for e in bundle.items}),
            "evidence_items": len(bundle.items),
            "used_memory": len(mem_results) > 0,
        }

        return response, metadata

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
