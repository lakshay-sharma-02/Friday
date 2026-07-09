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
        "RULES (must all hold):",
        "1. The <evidence> block below is the ONLY permitted source. It is "
        "AUTHORITATIVE; never contradict it.",
        "2. General knowledge is LOWER priority. If evidence conflicts with your "
        "model priors, TRUST THE EVIDENCE.",
        "3. Do NOT introduce any fact, memory trace, install record, dependency "
        "version, file state, or system state that is not present inside <evidence>. "
        "Never fabricate paths, branches, versions, or past events.",
        "4. Do NOT invent sections such as 'Memory:', 'History:', 'Installs:', or "
        "'Past attempts' unless that exact content appears inside <evidence>. If "
        "<evidence> has no memory items, do not write a memory section at all.",
        "5. If <evidence> does not contain what is needed to answer, state that "
        "plainly (e.g. 'The available evidence does not cover X.') instead of "
        "guessing or filling in from memory.",
        "6. Every claim in your answer must be traceable to a line inside "
        "<evidence>. When unsure whether something is in <evidence>, OMIT it. "
        "Never label invented content as 'from EVIDENCE'.",
        "",
    ]

    if evidence_section:
        parts.append("<evidence>")
        parts.append(evidence_section)
        parts.append("</evidence>")
        parts.append("")
    else:
        parts.append("<evidence>")
        parts.append("No evidence was collected.")
        parts.append("</evidence>")
        parts.append("")

    parts.append(f"User request: {query}")
    parts.append("")
    parts.append("Answer strictly from the <evidence> block above, following RULES 1-6.")

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
    ("DESIGN.md", "architecture"),
    ("CONTRIBUTING.md", "contributing"),
]


# Directories that are never part of "understanding" the repo.
_IGNORE_DIRS = {
    ".git", "node_modules", "target", "dist", "build", ".venv", "venv",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".tox", "site-packages", ".idea", ".vscode", "htmlcov", "coverage",
}

# Project metadata files whose presence reveals language/package manager.
_METADATA_FILES = [
    "pyproject.toml", "Cargo.toml", "package.json", "go.mod",
    "requirements.txt", "uv.lock", "poetry.lock", "Cargo.lock",
    "setup.py", "setup.cfg", "Gemfile", "pom.xml", "build.gradle",
]

_METADATA_MAX_BYTES = 4000


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


def collect_repository_evidence(
    cwd: str = ".",
    project_context: "ProjectContext" = None,
    workspace_state: "WorkspaceState" = None,
) -> EvidenceBundle:
    """Lightweight repository snapshot for grounded analysis/summary.

    Builds an OVERVIEW (tree, metadata, entry points, stats) - it does NOT
    recursively read source. Reuses ProjectContext for derived facts and only
    reads small, well-known metadata files. Safe to call on any repo.
    """
    bundle = EvidenceBundle()
    base = Path(cwd).resolve()

    if not base.exists():
        return bundle

    # --- Repository root + current working directory ---
    repo_root = _find_repo_root(base) or base
    bundle.add(EvidenceSource.WORKSPACE, "repo_root", str(repo_root), confidence=1.0)
    bundle.add(EvidenceSource.WORKSPACE, "cwd", str(base), confidence=1.0)

    # --- Top-level directory tree (one level, ignoring build artifacts) ---
    tree = _top_level_tree(base)
    if tree:
        bundle.add(EvidenceSource.WORKSPACE, "top_level_tree", tree, confidence=1.0)

    # --- Project metadata files (language / package manager inference) ---
    meta = {}
    for fname in _METADATA_FILES:
        path = base / fname
        if path.exists():
            try:
                size = path.stat().st_size
                if size <= _METADATA_MAX_BYTES:
                    meta[fname] = path.read_text(encoding="utf-8", errors="replace")
                else:
                    meta[fname] = f"<{fname}: {size} bytes, too large to inline>"
            except OSError:
                continue
    if meta:
        bundle.add(EvidenceSource.WORKSPACE, "project_metadata", meta, confidence=1.0)

    # --- Entry points (from ProjectContext if available, else recompute) ---
    if project_context is not None:
        entry_points = project_context.entry_points
        major_components = project_context.major_components
        if project_context.active_phase:
            bundle.add(EvidenceSource.WORKSPACE, "active_phase",
                       project_context.active_phase, confidence=1.0)
    else:
        entry_points = _find_entry_points(base)
        major_components = _find_major_components(base)

    if entry_points:
        bundle.add(EvidenceSource.WORKSPACE, "entry_points", entry_points, confidence=1.0)
    if major_components:
        bundle.add(EvidenceSource.WORKSPACE, "major_components",
                   major_components, confidence=1.0)

    # --- Lightweight statistics (no recursive file reads) ---
    stats = _repo_stats(base)
    bundle.add(EvidenceSource.WORKSPACE, "repo_stats", stats, confidence=1.0)

    # --- Language / package-manager hints from workspace state ---
    if workspace_state is not None:
        if workspace_state.project_type:
            bundle.add(EvidenceSource.WORKSPACE, "project_type",
                       workspace_state.project_type, confidence=1.0)
        if workspace_state.languages:
            bundle.add(EvidenceSource.WORKSPACE, "languages",
                       workspace_state.languages, confidence=1.0)
        if workspace_state.package_manager:
            bundle.add(EvidenceSource.WORKSPACE, "package_manager",
                       workspace_state.package_manager, confidence=1.0)
        if workspace_state.build_system:
            bundle.add(EvidenceSource.WORKSPACE, "build_system",
                       workspace_state.build_system, confidence=1.0)

    return bundle


def _find_repo_root(path: Path) -> Optional[Path]:
    """Walk up until a .git (or pyproject.toml/Cargo.toml) is found."""
    for parent in [path, *path.parents]:
        if (parent / ".git").exists():
            return parent
        if (parent / "pyproject.toml").exists() or (parent / "Cargo.toml").exists():
            return parent
    return None


def _top_level_tree(base: Path, max_entries: int = 60) -> list[str]:
    """One-level listing of top-level dirs and files, ignoring build artifacts."""
    entries = []
    try:
        for item in sorted(base.iterdir()):
            if item.name in _IGNORE_DIRS or item.name.startswith("."):
                continue
            entries.append(item.name + "/" if item.is_dir() else item.name)
    except (OSError, PermissionError):
        return []
    return entries[:max_entries]


def _find_entry_points(base: Path) -> list[str]:
    """Recompute likely entry points without a full ProjectContext."""
    candidates = [
        "main.py", "app.py", "server.py", "index.py", "__main__.py",
        "main.rs", "lib.rs", "index.js", "index.ts", "app.js",
        "server.js", "Main.java", "App.java", "main.go", "manage.py", "cli.py",
    ]
    found = []
    for c in candidates:
        if (base / c).exists():
            found.append(c)
    # Also surface a cmd/ or src/ entry if present.
    for sub in ("cmd", "src"):
        subp = base / sub
        if subp.is_dir():
            found.append(f"{sub}/")
    return found


def _find_major_components(base: Path) -> list[str]:
    """Top-level code directories (mirrors ProjectContext heuristic)."""
    components = []
    try:
        for item in base.iterdir():
            if not item.is_dir() or item.name in _IGNORE_DIRS or item.name.startswith("."):
                continue
            if any(item.glob("*.py")) or any(item.glob("*.rs")) or \
               any(item.glob("*.js")) or any(item.glob("*.ts")) or \
               any(item.glob("*.go")) or any(item.glob("*.java")):
                components.append(item.name)
    except (OSError, PermissionError):
        pass
    return components[:10]


def _repo_stats(base: Path, max_dirs_scan: int = 40) -> dict:
    """Cheap repo statistics without recursive source loading.

    Counts languages by file extension across the top-level code dirs only,
    plus total file/dir counts (still bounded - not a full index).
    """
    ext_count: dict[str, int] = {}
    file_total = 0
    dir_total = 0
    recent: list[str] = []

    try:
        for item in base.iterdir():
            if item.name in _IGNORE_DIRS or item.name.startswith("."):
                continue
            if item.is_dir():
                dir_total += 1
            else:
                file_total += 1
                _count_ext(item, ext_count)
    except (OSError, PermissionError):
        pass

    # Scan one level into code dirs only (bounded total) for language signal.
    scanned = 0
    for item in base.iterdir():
        if not item.is_dir() or item.name in _IGNORE_DIRS or item.name.startswith("."):
            continue
        if scanned >= max_dirs_scan:
            break
        try:
            for f in item.iterdir():
                if f.name.startswith("."):
                    continue
                if f.is_dir():
                    dir_total += 1
                else:
                    file_total += 1
                    _count_ext(f, ext_count)
                scanned += 1
                if scanned >= 400:  # hard cap on files touched
                    break
        except (OSError, PermissionError):
            continue

    stats = {
        "top_level_files": file_total,
        "top_level_dirs": dir_total,
        "languages_by_ext": dict(sorted(ext_count.items(), key=lambda x: -x[1])),
    }
    return stats


def _count_ext(path: Path, ext_count: dict) -> None:
    """Tally a file's extension into the counter."""
    if path.suffix:
        ext = path.suffix.lower()
        ext_count[ext] = ext_count.get(ext, 0) + 1
