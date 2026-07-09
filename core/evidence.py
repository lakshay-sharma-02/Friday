"""Evidence Collection - structured facts for LLM synthesis.

The LLM receives evidence, not guesses.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
from pathlib import Path


class EvidenceSource(Enum):
    """Where evidence came from."""
    MEMORY = "memory"
    WORKSPACE = "workspace"
    GIT = "git"
    FILESYSTEM = "filesystem"
    OBSERVERS = "observers"
    TOOL_OUTPUT = "tool_output"


@dataclass
class Evidence:
    """A single piece of grounded evidence."""
    source: EvidenceSource
    key: str
    value: Any
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)

    def to_prompt_line(self) -> str:
        """Format as a prompt line for LLM context."""
        if isinstance(self.value, (list, tuple)):
            value_str = ", ".join(str(v) for v in self.value)
        elif isinstance(self.value, dict):
            value_str = "; ".join(f"{k}={v}" for k, v in self.value.items())
        else:
            value_str = str(self.value)

        return f"{self.key}: {value_str}"


@dataclass
class EvidenceBundle:
    """Collection of evidence from multiple sources."""
    items: list[Evidence] = field(default_factory=list)

    def add(self, source: EvidenceSource, key: str, value: Any,
            confidence: float = 1.0, **metadata) -> None:
        """Add evidence to the bundle."""
        self.items.append(Evidence(
            source=source,
            key=key,
            value=value,
            confidence=confidence,
            metadata=metadata
        ))

    def get_by_source(self, source: EvidenceSource) -> list[Evidence]:
        """Get all evidence from a specific source."""
        return [e for e in self.items if e.source == source]

    def to_prompt_section(self) -> str:
        """Format as structured prompt section."""
        if not self.items:
            return ""

        lines = ["EVIDENCE"]

        # Group by source
        by_source = {}
        for item in self.items:
            source = item.source.value
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(item)

        # Format each source group
        for source_name, items in by_source.items():
            lines.append(f"\n{source_name.title()}:")
            for item in items:
                lines.append(f"  {item.to_prompt_line()}")

        return "\n".join(lines)

    def is_empty(self) -> bool:
        """Check if bundle has no evidence."""
        return len(self.items) == 0


def build_synthesis_prompt(bundle: EvidenceBundle, query: str) -> str:
    """Build a synthesis prompt that forces the LLM to stay grounded in evidence.

    The prompt (1) declares retrieved evidence authoritative, (2) forbids
    introducing facts not present in it, and (3) requires the model to say so
    when evidence is insufficient. This is the single source of truth for the
    "evidence precedence" rule (Part 4/5/9) across all synthesis queries.
    """
    evidence_section = bundle.to_prompt_section()

    parts = [
        "You are synthesizing an answer from RETRIEVED EVIDENCE only.",
        "",
        "RULES:",
        "1. Retrieved evidence is AUTHORITATIVE. Never contradict it.",
        "2. General knowledge is LOWER priority. If evidence conflicts with your "
        "model priors, TRUST THE EVIDENCE.",
        "3. Do NOT introduce any fact, memory trace, install record, file state, "
        "or system state that is not present in the EVIDENCE block below. "
        "Never fabricate paths, branches, versions, or past events.",
        "4. If the EVIDENCE does not contain what is needed to answer, state that "
        "plainly (e.g. 'The available evidence does not cover X.') instead of "
        "guessing or filling in from memory.",
        "",
    ]

    if evidence_section:
        parts.append(evidence_section)
        parts.append("")
    else:
        parts.append("No evidence was collected.")
        parts.append("")

    parts.append(f"User request: {query}")
    parts.append("")
    parts.append("Answer strictly from the EVIDENCE above, following RULES 1-4.")

    return "\n".join(parts)


def collect_memory_evidence(memory_manager, query: str) -> EvidenceBundle:
    """Collect evidence from memory system."""
    bundle = EvidenceBundle()

    try:
        results = memory_manager.search(query, limit=5)
        for result in results:
            content = result.get("content", result.get("text", ""))
            if content:
                bundle.add(
                    source=EvidenceSource.MEMORY,
                    key=result.get("type", "memory"),
                    value=content,
                    confidence=result.get("score", 1.0)
                )
    except Exception:
        pass

    return bundle


def collect_workspace_evidence(world_state: "WorldState",
                                project_context: "ProjectContext") -> EvidenceBundle:
    """Collect evidence from workspace state."""
    bundle = EvidenceBundle()
    ws = world_state.workspace

    bundle.add(EvidenceSource.WORKSPACE, "project_name", project_context.name)

    if project_context.purpose:
        bundle.add(EvidenceSource.WORKSPACE, "project_purpose", project_context.purpose)

    if project_context.active_phase:
        bundle.add(EvidenceSource.WORKSPACE, "current_phase", project_context.active_phase)

    if ws.project_type:
        bundle.add(EvidenceSource.WORKSPACE, "project_type", ws.project_type)

    if ws.languages:
        bundle.add(EvidenceSource.WORKSPACE, "languages", ws.languages)

    if ws.package_manager:
        bundle.add(EvidenceSource.WORKSPACE, "package_manager", ws.package_manager)

    if ws.build_system:
        bundle.add(EvidenceSource.WORKSPACE, "build_system", ws.build_system)

    return bundle


def collect_git_evidence(world_state: "WorldState") -> EvidenceBundle:
    """Collect evidence from git state."""
    bundle = EvidenceBundle()
    ws = world_state.workspace

    if ws.is_git_repo:
        bundle.add(EvidenceSource.GIT, "is_git_repo", True)

        if ws.git_branch:
            bundle.add(EvidenceSource.GIT, "branch", ws.git_branch)

        if ws.git_clean is not None:
            status = "clean" if ws.git_clean else "dirty"
            bundle.add(EvidenceSource.GIT, "status", status)

        if ws.git_modified_files:
            bundle.add(EvidenceSource.GIT, "modified_files", len(ws.git_modified_files))

    return bundle


def collect_system_evidence(world_state: "WorldState") -> EvidenceBundle:
    """Collect evidence from system observers."""
    bundle = EvidenceBundle()
    comp = world_state.computer
    net = world_state.network

    if comp.ram_gb:
        bundle.add(EvidenceSource.OBSERVERS, "ram_gb", comp.ram_gb)

    if comp.logical_cores:
        bundle.add(EvidenceSource.OBSERVERS, "cpu_cores", comp.logical_cores)

    if comp.disk_use_percent:
        bundle.add(EvidenceSource.OBSERVERS, "disk_usage", comp.disk_use_percent)

    if comp.battery_percent:
        bundle.add(EvidenceSource.OBSERVERS, "battery", comp.battery_percent)

    if comp.os:
        bundle.add(EvidenceSource.OBSERVERS, "os", comp.os)

    bundle.add(EvidenceSource.OBSERVERS, "internet", net.internet_reachable)

    return bundle


_DOC_CANDIDATES = [
    ("README.md", "readme"),
    ("README.txt", "readme"),
    ("README", "readme"),
    ("CLAUDE.md", "claude_md"),
    ("ARCHITECTURE.md", "architecture"),
    ("SYSTEM_ARCHITECTURE.md", "architecture"),
    ("PHASE10_ARCHITECTURE_DIAGRAM.md", "architecture"),
]


def collect_document_evidence(cwd: str = ".") -> EvidenceBundle:
    """Collect evidence from project documents (README, architecture, CLAUDE.md).

    Reads real files from disk - authoritative project-level context.
    """
    bundle = EvidenceBundle()
    base = Path(cwd).resolve()

    if not base.exists():
        return bundle

    for filename, key in _DOC_CANDIDATES:
        path = base / filename
        if path.exists():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            # Cap content so we don't flood the prompt.
            excerpt = text[:2000]
            bundle.add(
                EvidenceSource.WORKSPACE,
                key,
                excerpt,
                confidence=1.0,
                path=str(path),
            )

    return bundle
