"""Evidence Providers - lightweight adapters to existing Friday subsystems.

This is an EXPERIMENTAL module for testing evidence-based routing.
Providers are thin adapters that declare what evidence they can provide.
All logic delegates to existing implementations - NO duplication.
"""

from typing import Dict, Any, Optional, List
from core.evidence_types import EvidenceType


class EvidenceProvider:
    """Base class for evidence providers."""

    def provides(self) -> List[EvidenceType]:
        """Return list of evidence types this provider can supply."""
        raise NotImplementedError

    async def collect(self, query: str) -> Dict[str, Any]:
        """Collect evidence. Returns dict with evidence data."""
        raise NotImplementedError


class MemoryProvider(EvidenceProvider):
    """Provides user profile and preferences from memory subsystem."""

    def provides(self) -> List[EvidenceType]:
        return [EvidenceType.USER_PROFILE, EvidenceType.USER_PREFERENCES]

    async def collect(self, query: str) -> Dict[str, Any]:
        """Delegate to existing MemoryManager."""
        from memory.manager import MemoryManager
        import asyncio

        manager = MemoryManager()
        results = await asyncio.to_thread(manager.search, query, limit=5)

        return {
            "source": "memory",
            "memories": results,
            "count": len(results)
        }


class SystemProvider(EvidenceProvider):
    """Provides system state from observers."""

    def provides(self) -> List[EvidenceType]:
        return [EvidenceType.SYSTEM_STATE]

    async def collect(self, query: str) -> Dict[str, Any]:
        """Delegate to existing WorldState observation."""
        from core.world_manager import observe_world
        from core.world import RuntimeState

        world = await observe_world(cwd=".", runtime=RuntimeState())

        return {
            "source": "system",
            "computer": {
                "ram_gb": world.computer.ram_gb,
                "logical_cores": world.computer.logical_cores,
                "disk_use_percent": world.computer.disk_use_percent,
                "battery_percent": world.computer.battery_percent,
            },
            "network": {
                "internet_reachable": world.network.internet_reachable
            }
        }


class WorkspaceProvider(EvidenceProvider):
    """Provides workspace and project metadata from observers."""

    def provides(self) -> List[EvidenceType]:
        return [EvidenceType.WORKSPACE, EvidenceType.PROJECT_METADATA]

    async def collect(self, query: str) -> Dict[str, Any]:
        """Delegate to existing WorldState and ProjectContext."""
        from core.world_manager import observe_world
        from core.world import RuntimeState
        from core.project_context import ProjectContext

        world = await observe_world(cwd=".", runtime=RuntimeState())
        project_context = ProjectContext.from_workspace(world.workspace, ".")

        return {
            "source": "workspace",
            "workspace": {
                "project_type": world.workspace.project_type,
                "languages": world.workspace.languages,
                "cwd": world.workspace.cwd,
            },
            "project": {
                "name": project_context.name,
                "purpose": project_context.purpose,
                "active_phase": project_context.active_phase,
            }
        }


class GitProvider(EvidenceProvider):
    """Provides git state from workspace observers."""

    def provides(self) -> List[EvidenceType]:
        return [EvidenceType.GIT]

    async def collect(self, query: str) -> Dict[str, Any]:
        """Delegate to existing WorldState git information."""
        from core.world_manager import observe_world
        from core.world import RuntimeState

        world = await observe_world(cwd=".", runtime=RuntimeState())

        return {
            "source": "git",
            "is_git_repo": world.workspace.is_git_repo,
            "git_branch": world.workspace.git_branch,
            "git_clean": world.workspace.git_clean,
            "git_modified_files": world.workspace.git_modified_files,
        }


class RepositoryProvider(EvidenceProvider):
    """Provides repository structure and architecture analysis."""

    def provides(self) -> List[EvidenceType]:
        return [EvidenceType.REPOSITORY, EvidenceType.ARCHITECTURE]

    async def collect(self, query: str) -> Dict[str, Any]:
        """Delegate to existing ProjectContext and Evidence collection."""
        from core.world_manager import observe_world
        from core.world import RuntimeState
        from core.project_context import ProjectContext

        world = await observe_world(cwd=".", runtime=RuntimeState())
        project_context = ProjectContext.from_workspace(world.workspace, ".")

        return {
            "source": "repository",
            "project": {
                "name": project_context.name,
                "purpose": project_context.purpose,
                "languages": world.workspace.languages,
                "project_type": world.workspace.project_type,
            },
            "structure": {
                "languages": world.workspace.languages,
                "build_system": world.workspace.build_system,
                "test_runner": world.workspace.test_runner,
            }
        }


# Global provider registry
_PROVIDERS = [
    MemoryProvider(),
    SystemProvider(),
    WorkspaceProvider(),
    GitProvider(),
    RepositoryProvider(),
]


def get_providers_for_evidence(evidence_type: EvidenceType) -> List[EvidenceProvider]:
    """Get all providers that can supply a given evidence type."""
    return [p for p in _PROVIDERS if evidence_type in p.provides()]
