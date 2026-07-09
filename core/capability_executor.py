"""Capability Executor - executes capabilities using their owning subsystems.

Phase 10: Unified execution that respects ownership boundaries.
Never duplicates functionality - routes to existing subsystems.
"""

import asyncio
from typing import Any, Optional, Tuple
from dataclasses import dataclass

from core.capability_registry import CapabilityMetadata, CapabilityCategory
from core.world import WorldState
from core.project_context import ProjectContext
from memory.manager import MemoryManager


@dataclass
class CapabilityResult:
    """Result of capability execution."""
    success: bool
    data: Any  # Structured evidence or final answer
    source: str  # Which subsystem provided the answer
    latency_ms: float
    used_llm: bool = False
    error: Optional[str] = None


class CapabilityExecutor:
    """Executes capabilities by delegating to their owning subsystems.

    Never duplicates functionality. Always respects ownership boundaries.
    """

    def __init__(self):
        self.memory_manager = MemoryManager()

    async def execute(
        self,
        capability: CapabilityMetadata,
        query: str,
        world: Optional[WorldState] = None,
        project_context: Optional[ProjectContext] = None,
    ) -> CapabilityResult:
        """Execute a capability using its owning subsystem.

        Args:
            capability: The capability to execute
            query: Original user query
            world: Optional WorldState (for system state queries)
            project_context: Optional ProjectContext (for workspace queries)

        Returns:
            CapabilityResult with structured data or error
        """
        import time

        start = time.perf_counter()

        try:
            # Route to appropriate executor based on category
            if capability.category == CapabilityCategory.SYSTEM_STATE:
                result = await self._execute_system_state(capability, world)

            elif capability.category == CapabilityCategory.WORKSPACE:
                result = await self._execute_workspace(capability, world, project_context)

            elif capability.category == CapabilityCategory.GIT:
                result = await self._execute_git(capability, world)

            elif capability.category == CapabilityCategory.MEMORY:
                result = await self._execute_memory(capability, query)

            elif capability.category == CapabilityCategory.FILESYSTEM:
                result = await self._execute_filesystem(capability, query)

            elif capability.category == CapabilityCategory.KNOWLEDGE:
                result = await self._execute_knowledge(capability, query)

            else:
                result = CapabilityResult(
                    success=False,
                    data=None,
                    source=capability.owner_module,
                    latency_ms=0,
                    error=f"Unsupported category: {capability.category}"
                )

            # Calculate latency
            latency_ms = (time.perf_counter() - start) * 1000
            result.latency_ms = latency_ms

            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return CapabilityResult(
                success=False,
                data=None,
                source=capability.owner_module,
                latency_ms=latency_ms,
                error=str(e)
            )

    async def _execute_system_state(
        self, capability: CapabilityMetadata, world: Optional[WorldState]
    ) -> CapabilityResult:
        """Execute system state capability (RAM, CPU, disk, battery, network)."""
        if not world:
            return CapabilityResult(
                success=False,
                data=None,
                source=capability.owner_module,
                latency_ms=0,
                error="WorldState not available"
            )

        # Direct access to WorldState fields
        data = None
        if capability.name == "system_ram":
            data = {"ram_gb": world.computer.ram_gb}
        elif capability.name == "system_cpu":
            data = {"logical_cores": world.computer.logical_cores}
        elif capability.name == "system_disk":
            data = {
                "disk_total": world.computer.disk_total,
                "disk_used": world.computer.disk_used,
                "disk_available": world.computer.disk_available,
                "disk_use_percent": world.computer.disk_use_percent
            }
        elif capability.name == "system_battery":
            data = {"battery_percent": world.computer.battery_percent}
        elif capability.name == "system_network":
            data = {
                "internet_reachable": world.network.internet_reachable,
                "hostname": world.network.hostname,
                "local_ip": world.network.local_ip
            }

        return CapabilityResult(
            success=True,
            data=data,
            source="WorldState (observers)",
            latency_ms=0  # Will be calculated by caller
        )

    async def _execute_workspace(
        self,
        capability: CapabilityMetadata,
        world: Optional[WorldState],
        project_context: Optional[ProjectContext]
    ) -> CapabilityResult:
        """Execute workspace capability (project, phase, languages, type)."""
        data = None

        if capability.name == "workspace_project":
            if project_context:
                data = {
                    "name": project_context.name,
                    "purpose": project_context.purpose
                }
        elif capability.name == "workspace_phase":
            if project_context:
                data = {"active_phase": project_context.active_phase}
        elif capability.name == "workspace_languages":
            if world:
                data = {"languages": world.workspace.languages}
        elif capability.name == "workspace_type":
            if world:
                data = {"project_type": world.workspace.project_type}

        return CapabilityResult(
            success=data is not None,
            data=data,
            source="ProjectContext / WorkspaceState",
            latency_ms=0
        )

    async def _execute_git(
        self, capability: CapabilityMetadata, world: Optional[WorldState]
    ) -> CapabilityResult:
        """Execute git capability (branch, status)."""
        if not world or not world.workspace.is_git_repo:
            return CapabilityResult(
                success=False,
                data=None,
                source="WorkspaceState",
                latency_ms=0,
                error="Not a git repository"
            )

        data = None
        if capability.name == "git_branch":
            data = {"branch": world.workspace.git_branch}
        elif capability.name == "git_status":
            data = {
                "branch": world.workspace.git_branch,
                "clean": world.workspace.git_clean,
                "modified_files": len(world.workspace.git_modified_files)
            }

        return CapabilityResult(
            success=data is not None,
            data=data,
            source="WorkspaceState (git observer)",
            latency_ms=0
        )

    async def _execute_memory(
        self, capability: CapabilityMetadata, query: str
    ) -> CapabilityResult:
        """Execute memory capability (recall teachings, preferences)."""
        # Memory search
        results = await asyncio.to_thread(self.memory_manager.search, query, limit=5)

        data = {
            "memories": [
                {"type": r.get("type"), "content": r.get("content")}
                for r in results
            ]
        }

        return CapabilityResult(
            success=True,
            data=data,
            source="MemoryManager",
            latency_ms=0,
            used_llm=False  # Memory search is retrieval, not LLM
        )

    async def _execute_filesystem(
        self, capability: CapabilityMetadata, query: str
    ) -> CapabilityResult:
        """Execute filesystem capability.

        Note: This marks that tools are needed but doesn't execute them.
        Actual tool execution happens through Executor (via Pipeline).
        """
        return CapabilityResult(
            success=False,
            data=None,
            source="tools.files (requires Executor)",
            latency_ms=0,
            error="Filesystem operations require Executor - use Pipeline"
        )

    async def _execute_knowledge(
        self, capability: CapabilityMetadata, query: str
    ) -> CapabilityResult:
        """Execute knowledge capability (conceptual questions via LLM)."""
        from core.model_client import call_model

        # Direct LLM call for conceptual knowledge - stream to stdout
        answer = await call_model(query, enable_thinking=False, stream_to_stdout=True)

        return CapabilityResult(
            success=True,
            data={"answer": answer},
            source="LLM (conceptual knowledge)",
            latency_ms=0,
            used_llm=True
        )


def format_capability_result(result: CapabilityResult, capability: CapabilityMetadata) -> str:
    """Format capability result for user display."""
    if not result.success:
        return f"Error: {result.error}"

    # Format based on data structure
    if isinstance(result.data, dict):
        if "answer" in result.data:
            # LLM knowledge result
            return result.data["answer"]
        elif "memories" in result.data:
            # Memory result
            memories = result.data["memories"]
            if not memories:
                return "No memories found."
            lines = []
            for mem in memories:
                lines.append(f"- {mem['content']}")
            return "\n".join(lines)
        else:
            # Structured data result
            lines = []
            for key, value in result.data.items():
                if value is not None:
                    lines.append(f"{key}: {value}")
            return "\n".join(lines)

    return str(result.data)
