"""Evidence Providers - lightweight adapters for existing capabilities.

EXPERIMENT ONLY - Can be removed if experiment fails.
Reuses existing implementations without duplicating logic.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from experimental.evidence_types import EvidenceType


@dataclass
class Evidence:
    """Single piece of evidence collected from a provider."""
    type: EvidenceType
    data: Any
    source: str
    confidence: float = 1.0


class MemoryProvider:
    """Provides USER_PROFILE and USER_PREFERENCES evidence.

    Reuses: memory.manager.MemoryManager
    """

    def __init__(self):
        from memory.manager import MemoryManager
        self.memory = MemoryManager()

    def provides(self) -> List[EvidenceType]:
        return [EvidenceType.USER_PROFILE, EvidenceType.USER_PREFERENCES]

    async def collect(self, query: str, evidence_types: List[EvidenceType]) -> List[Evidence]:
        """Collect memory-based evidence."""
        import asyncio

        results = []

        if not any(et in evidence_types for et in self.provides()):
            return results

        # Search memory
        memories = await asyncio.to_thread(self.memory.search, query, limit=5)

        for mem in memories:
            mem_type = mem.get("type", "")

            if mem_type in ["teaching", "preference"]:
                evidence_type = EvidenceType.USER_PREFERENCES
            elif mem_type in ["identity", "profile"]:
                evidence_type = EvidenceType.USER_PROFILE
            else:
                evidence_type = EvidenceType.USER_PROFILE

            if evidence_type in evidence_types:
                results.append(Evidence(
                    type=evidence_type,
                    data=mem,
                    source="MemoryManager",
                    confidence=mem.get("score", 1.0)
                ))

        return results


class SystemProvider:
    """Provides SYSTEM_STATE evidence.

    Reuses: core.world.WorldState (observers)
    """

    def provides(self) -> List[EvidenceType]:
        return [EvidenceType.SYSTEM_STATE]

    async def collect(self, query: str, evidence_types: List[EvidenceType]) -> List[Evidence]:
        """Collect system state evidence."""
        if EvidenceType.SYSTEM_STATE not in evidence_types:
            return []

        from core.world_manager import observe_world
        from core.world import RuntimeState

        world = await observe_world(cwd=".", runtime=RuntimeState())

        return [Evidence(
            type=EvidenceType.SYSTEM_STATE,
            data={
                "ram_gb": world.computer.ram_gb,
                "logical_cores": world.computer.logical_cores,
                "os": world.computer.os,
                "disk_use_percent": world.computer.disk_use_percent,
                "battery_percent": world.computer.battery_percent,
                "internet_reachable": world.network.internet_reachable,
            },
            source="WorldState (observers)"
        )]


class WorkspaceProvider:
    """Provides WORKSPACE and PROJECT_METADATA evidence.

    Reuses: core.world.WorkspaceState, core.project_context.ProjectContext
    """

    def provides(self) -> List[EvidenceType]:
        return [EvidenceType.WORKSPACE, EvidenceType.PROJECT_METADATA]

    async def collect(self, query: str, evidence_types: List[EvidenceType]) -> List[Evidence]:
        """Collect workspace evidence."""
        if not any(et in evidence_types for et in self.provides()):
            return []

        from core.world_manager import observe_world
        from core.world import RuntimeState
        from core.project_context import ProjectContext

        world = await observe_world(cwd=".", runtime=RuntimeState())
        project = ProjectContext.from_workspace(world.workspace, ".")

        results = []

        if EvidenceType.WORKSPACE in evidence_types:
            results.append(Evidence(
                type=EvidenceType.WORKSPACE,
                data={
                    "cwd": world.workspace.cwd,
                    "project_type": world.workspace.project_type,
                    "languages": world.workspace.languages,
                },
                source="WorkspaceState"
            ))

        if EvidenceType.PROJECT_METADATA in evidence_types:
            results.append(Evidence(
                type=EvidenceType.PROJECT_METADATA,
                data={
                    "name": project.name,
                    "purpose": project.purpose,
                    "active_phase": project.active_phase,
                },
                source="ProjectContext"
            ))

        return results


class GitProvider:
    """Provides GIT evidence.

    Reuses: core.world.WorkspaceState (git observer)
    """

    def provides(self) -> List[EvidenceType]:
        return [EvidenceType.GIT]

    async def collect(self, query: str, evidence_types: List[EvidenceType]) -> List[Evidence]:
        """Collect git evidence."""
        if EvidenceType.GIT not in evidence_types:
            return []

        from core.world_manager import observe_world
        from core.world import RuntimeState

        world = await observe_world(cwd=".", runtime=RuntimeState())

        if not world.workspace.is_git_repo:
            return []

        return [Evidence(
            type=EvidenceType.GIT,
            data={
                "branch": world.workspace.git_branch,
                "clean": world.workspace.git_clean,
                "modified_files": world.workspace.git_modified_files,
            },
            source="WorkspaceState (git observer)"
        )]


class RepositoryProvider:
    """Provides REPOSITORY and ARCHITECTURE evidence.

    Reuses: core.evidence collection functions
    """

    def provides(self) -> List[EvidenceType]:
        return [EvidenceType.REPOSITORY, EvidenceType.ARCHITECTURE]

    async def collect(self, query: str, evidence_types: List[EvidenceType]) -> List[Evidence]:
        """Collect repository evidence."""
        if not any(et in evidence_types for et in self.provides()):
            return []

        from core.world_manager import observe_world
        from core.world import RuntimeState
        from core.project_context import ProjectContext
        from core.evidence import collect_repository_evidence

        world = await observe_world(cwd=".", runtime=RuntimeState())
        project = ProjectContext.from_workspace(world.workspace, ".")

        bundle = collect_repository_evidence(".", project, world.workspace)

        results = []
        for item in bundle.items:
            if item.source.value == "repository_snapshot":
                results.append(Evidence(
                    type=EvidenceType.REPOSITORY,
                    data=item.data,
                    source="repository_snapshot"
                ))
            elif item.source.value == "architecture":
                results.append(Evidence(
                    type=EvidenceType.ARCHITECTURE,
                    data=item.data,
                    source="architecture"
                ))

        return results
