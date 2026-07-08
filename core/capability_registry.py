"""Capability Registry - metadata-driven capability definitions.

Phase 10: Capability Layer. Every capability declares its owner, requirements, and metadata.
The router reasons over this metadata instead of hardcoded patterns.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any, Set
from core.operations import Operation


class CapabilityCategory(Enum):
    """High-level capability categories."""
    SYSTEM_STATE = "system_state"  # RAM, CPU, disk, battery, network
    WORKSPACE = "workspace"  # Project context, languages, build systems
    GIT = "git"  # Version control state and operations
    MEMORY = "memory"  # Teachings, lessons, preferences
    FILESYSTEM = "filesystem"  # File operations, search
    PROCESS = "process"  # Process management
    KNOWLEDGE = "knowledge"  # Conceptual knowledge (LLM)
    EXECUTION = "execution"  # Multi-step task execution


class LatencyCategory(Enum):
    """Expected latency for capability execution."""
    INSTANT = "instant"  # <10ms (in-memory data)
    FAST = "fast"  # <100ms (simple computation)
    MODERATE = "moderate"  # <1s (tool execution)
    SLOW = "slow"  # >1s (LLM, complex operations)


@dataclass
class CapabilityMetadata:
    """Metadata describing a capability's characteristics and requirements."""

    # Identity
    name: str
    category: CapabilityCategory
    description: str

    # Ownership
    owner_module: str  # e.g., "core.world", "memory.manager"
    authoritative_source: str  # e.g., "WorldState.computer.ram_gb"

    # Requirements
    requires_planner: bool = False
    requires_executor: bool = False
    requires_llm: bool = False
    requires_tools: list[str] = field(default_factory=list)

    # Characteristics
    produces_evidence: bool = True
    latency: LatencyCategory = LatencyCategory.INSTANT

    # Semantic matching
    keywords: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)

    # Phase 10.5: Supported operations
    supported_operations: Set[Operation] = field(default_factory=set)

    # Access function (optional - for direct queries)
    accessor: Optional[Callable] = None


class CapabilityRegistry:
    """Central registry of all Friday capabilities.

    Capabilities register their metadata here. The Capability Router
    reasons over this metadata to determine routing decisions.
    """

    def __init__(self):
        self._capabilities: dict[str, CapabilityMetadata] = {}
        self._register_core_capabilities()

    def register(self, capability: CapabilityMetadata) -> None:
        """Register a capability."""
        self._capabilities[capability.name] = capability

    def get(self, name: str) -> Optional[CapabilityMetadata]:
        """Get capability by name."""
        return self._capabilities.get(name)

    def get_by_category(self, category: CapabilityCategory) -> list[CapabilityMetadata]:
        """Get all capabilities in a category."""
        return [c for c in self._capabilities.values() if c.category == category]

    def find_by_keywords(self, query: str) -> list[CapabilityMetadata]:
        """Find capabilities matching keywords in query."""
        query_lower = query.lower()
        matches = []

        for capability in self._capabilities.values():
            # Check keywords
            if any(kw in query_lower for kw in capability.keywords):
                matches.append(capability)
                continue

            # Check synonyms
            if any(syn in query_lower for syn in capability.synonyms):
                matches.append(capability)
                continue

        return matches

    def list_all(self) -> list[CapabilityMetadata]:
        """List all registered capabilities."""
        return list(self._capabilities.values())

    def _register_core_capabilities(self):
        """Register Friday's core capabilities."""

        # System State Capabilities
        self.register(CapabilityMetadata(
            name="system_ram",
            category=CapabilityCategory.SYSTEM_STATE,
            description="Current RAM usage and availability",
            owner_module="observers.computer",
            authoritative_source="WorldState.computer.ram_gb",
            requires_planner=False,
            requires_executor=False,
            requires_llm=False,
            latency=LatencyCategory.INSTANT,
            keywords=["ram", "ram usage", "available memory"],
            synonyms=["memory usage", "mem"],
            supported_operations={Operation.READ, Operation.INSPECT}
        ))

        self.register(CapabilityMetadata(
            name="system_cpu",
            category=CapabilityCategory.SYSTEM_STATE,
            description="CPU cores and usage",
            owner_module="observers.computer",
            authoritative_source="WorldState.computer.logical_cores",
            requires_planner=False,
            requires_executor=False,
            requires_llm=False,
            latency=LatencyCategory.INSTANT,
            keywords=["cpu", "processor", "cores"],
            synonyms=["processor", "cpu cores"],
            supported_operations={Operation.READ, Operation.INSPECT}
        ))

        self.register(CapabilityMetadata(
            name="system_disk",
            category=CapabilityCategory.SYSTEM_STATE,
            description="Disk usage and availability",
            owner_module="observers.computer",
            authoritative_source="WorldState.computer.disk_use_percent",
            requires_planner=False,
            requires_executor=False,
            requires_llm=False,
            latency=LatencyCategory.INSTANT,
            keywords=["disk", "storage", "disk space"],
            synonyms=["disk usage", "storage", "hard drive"],
            supported_operations={Operation.READ, Operation.INSPECT}
        ))

        self.register(CapabilityMetadata(
            name="system_battery",
            category=CapabilityCategory.SYSTEM_STATE,
            description="Battery status and percentage",
            owner_module="observers.computer",
            authoritative_source="WorldState.computer.battery_percent",
            requires_planner=False,
            requires_executor=False,
            requires_llm=False,
            latency=LatencyCategory.INSTANT,
            keywords=["battery", "power", "battery level"],
            synonyms=["battery percent", "battery status", "power level"],
            supported_operations={Operation.READ, Operation.INSPECT}
        ))

        self.register(CapabilityMetadata(
            name="system_network",
            category=CapabilityCategory.SYSTEM_STATE,
            description="Network connectivity status",
            owner_module="observers.network",
            authoritative_source="WorldState.network.internet_reachable",
            requires_planner=False,
            requires_executor=False,
            requires_llm=False,
            latency=LatencyCategory.INSTANT,
            keywords=["network", "internet", "connectivity", "online"],
            synonyms=["internet status", "connection", "wifi"],
            supported_operations={Operation.READ, Operation.INSPECT}
        ))

        # Workspace Capabilities
        self.register(CapabilityMetadata(
            name="workspace_project",
            category=CapabilityCategory.WORKSPACE,
            description="Current project name and context",
            owner_module="core.project_context",
            authoritative_source="ProjectContext.name",
            requires_planner=False,
            requires_executor=False,
            requires_llm=False,
            latency=LatencyCategory.INSTANT,
            keywords=["project", "project name", "current project"],
            synonyms=["project name", "what project", "which project"],
            supported_operations={Operation.READ, Operation.SUMMARIZE}
        ))

        self.register(CapabilityMetadata(
            name="workspace_phase",
            category=CapabilityCategory.WORKSPACE,
            description="Current project phase or milestone",
            owner_module="core.project_context",
            authoritative_source="ProjectContext.active_phase",
            requires_planner=False,
            requires_executor=False,
            requires_llm=False,
            latency=LatencyCategory.INSTANT,
            keywords=["phase", "milestone", "current phase"],
            synonyms=["what phase", "which phase", "current milestone"],
            supported_operations={Operation.READ}
        ))

        self.register(CapabilityMetadata(
            name="workspace_languages",
            category=CapabilityCategory.WORKSPACE,
            description="Programming languages used in project",
            owner_module="observers.workspace",
            authoritative_source="WorldState.workspace.languages",
            requires_planner=False,
            requires_executor=False,
            requires_llm=False,
            latency=LatencyCategory.INSTANT,
            keywords=["languages", "programming languages"],
            synonyms=["what languages", "which languages", "language"],
            supported_operations={Operation.READ}
        ))

        self.register(CapabilityMetadata(
            name="workspace_type",
            category=CapabilityCategory.WORKSPACE,
            description="Project type (python, rust, etc.)",
            owner_module="observers.workspace",
            authoritative_source="WorldState.workspace.project_type",
            requires_planner=False,
            requires_executor=False,
            requires_llm=False,
            latency=LatencyCategory.INSTANT,
            keywords=["project type", "type of project"],
            synonyms=["what type", "project kind"],
            supported_operations={Operation.READ}
        ))

        # Git Capabilities
        self.register(CapabilityMetadata(
            name="git_branch",
            category=CapabilityCategory.GIT,
            description="Current git branch",
            owner_module="observers.workspace",
            authoritative_source="WorldState.workspace.git_branch",
            requires_planner=False,
            requires_executor=False,
            requires_llm=False,
            latency=LatencyCategory.INSTANT,
            keywords=["branch", "git branch", "current branch"],
            synonyms=["what branch", "which branch"],
            supported_operations={Operation.READ, Operation.INSPECT}
        ))

        self.register(CapabilityMetadata(
            name="git_status",
            category=CapabilityCategory.GIT,
            description="Git repository status (clean/dirty)",
            owner_module="observers.workspace",
            authoritative_source="WorldState.workspace.git_clean",
            requires_planner=False,
            requires_executor=False,
            requires_llm=False,
            latency=LatencyCategory.INSTANT,
            keywords=["git status", "git clean", "git dirty", "uncommitted"],
            synonyms=["repo status", "repository status", "working tree"],
            supported_operations={Operation.READ, Operation.INSPECT}
        ))

        self.register(CapabilityMetadata(
            name="git_operations",
            category=CapabilityCategory.GIT,
            description="Git operations (commit, diff, log, etc.)",
            owner_module="tools.git",
            authoritative_source="git tools",
            requires_planner=True,
            requires_executor=True,
            requires_llm=False,
            requires_tools=["git_commit", "git_diff", "git_log", "git_add"],
            latency=LatencyCategory.MODERATE,
            keywords=["git commit", "git diff", "git log", "git add"],
            synonyms=["commit", "diff", "log"],
            supported_operations={Operation.EXECUTE, Operation.MODIFY, Operation.INSPECT, Operation.COMPARE}
        ))

        # Memory Capabilities
        self.register(CapabilityMetadata(
            name="memory_recall",
            category=CapabilityCategory.MEMORY,
            description="Recall teachings, lessons, and preferences",
            owner_module="memory.manager",
            authoritative_source="MemoryManager.search()",
            requires_planner=False,
            requires_executor=False,
            requires_llm=True,  # LLM synthesizes memory results
            latency=LatencyCategory.FAST,
            keywords=["remember", "taught", "teach", "preference", "recall"],
            synonyms=["my name", "what did i", "do you remember"],
            supported_operations={Operation.RECALL, Operation.REMEMBER, Operation.REFLECT, Operation.ADVISE}
        ))

        # Filesystem Capabilities
        self.register(CapabilityMetadata(
            name="filesystem_search",
            category=CapabilityCategory.FILESYSTEM,
            description="Search for files or code",
            owner_module="tools.files",
            authoritative_source="search_files tool",
            requires_planner=False,  # Can be triggered directly
            requires_executor=True,
            requires_llm=False,
            requires_tools=["search_files"],
            latency=LatencyCategory.MODERATE,
            keywords=["where is", "find", "search", "locate", "memorymanager"],
            synonyms=["where is", "find file", "search for", "locate", "find class", "find function"],
            supported_operations={Operation.SEARCH, Operation.LOOKUP}
        ))

        self.register(CapabilityMetadata(
            name="filesystem_read",
            category=CapabilityCategory.FILESYSTEM,
            description="Read file contents",
            owner_module="tools.files",
            authoritative_source="read_file tool",
            requires_planner=False,
            requires_executor=True,
            requires_llm=False,
            requires_tools=["read_file"],
            latency=LatencyCategory.FAST,
            keywords=["read", "show", "cat", "view file"],
            synonyms=["read file", "show file", "view"],
            supported_operations={Operation.READ, Operation.INSPECT}
        ))

        self.register(CapabilityMetadata(
            name="filesystem_write",
            category=CapabilityCategory.FILESYSTEM,
            description="Write or modify files",
            owner_module="tools.files",
            authoritative_source="write_file tool",
            requires_planner=True,
            requires_executor=True,
            requires_llm=False,
            requires_tools=["write_file", "replace_in_file"],
            latency=LatencyCategory.MODERATE,
            keywords=["write", "create", "modify", "edit", "update file"],
            synonyms=["write file", "create file", "edit file"],
            supported_operations={Operation.MODIFY, Operation.EXECUTE}
        ))

        # Knowledge Capabilities
        self.register(CapabilityMetadata(
            name="conceptual_knowledge",
            category=CapabilityCategory.KNOWLEDGE,
            description="Conceptual knowledge and explanations",
            owner_module="core.model_client",
            authoritative_source="LLM",
            requires_planner=False,
            requires_executor=False,
            requires_llm=True,
            produces_evidence=False,
            latency=LatencyCategory.SLOW,
            keywords=["explain", "what is", "how does", "why", "concept"],
            synonyms=["explain", "tell me about", "describe"],
            supported_operations={Operation.EXPLAIN, Operation.COMPARE, Operation.ANALYZE, Operation.ADVISE}
        ))

        # Execution Capabilities
        self.register(CapabilityMetadata(
            name="multi_step_task",
            category=CapabilityCategory.EXECUTION,
            description="Complex multi-step task execution",
            owner_module="core.pipeline",
            authoritative_source="Pipeline + Planner + Executor",
            requires_planner=True,
            requires_executor=True,
            requires_llm=True,
            latency=LatencyCategory.SLOW,
            keywords=["install", "setup", "configure", "build", "deploy", "changed", "review repository", "summarize project"],
            synonyms=["execute", "run", "perform", "what changed"],
            supported_operations={Operation.EXECUTE, Operation.MODIFY, Operation.PLAN, Operation.REVIEW, Operation.SUMMARIZE}
        ))


# Global registry instance
_registry = CapabilityRegistry()


def get_capability_registry() -> CapabilityRegistry:
    """Get the global capability registry."""
    return _registry
