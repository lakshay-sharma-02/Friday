"""Project Context - intelligent understanding of the active project.

Exposes project-level intelligence without LLM guesswork.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os


@dataclass
class ProjectContext:
    """Structured context about the current project."""
    name: str
    purpose: Optional[str] = None
    project_type: Optional[str] = None
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_manager: Optional[str] = None
    build_system: Optional[str] = None
    test_runner: Optional[str] = None
    entry_points: list[str] = field(default_factory=list)
    major_components: list[str] = field(default_factory=list)
    active_phase: Optional[str] = None
    workspace_path: str = "."

    @classmethod
    def from_workspace(cls, workspace_state: "WorkspaceState", cwd: str = ".") -> "ProjectContext":
        """Build ProjectContext from WorkspaceState."""
        project_name = cls._infer_project_name(cwd)
        purpose = cls._infer_purpose(cwd)
        active_phase = cls._infer_phase(cwd)
        entry_points = cls._find_entry_points(cwd, workspace_state.project_type)
        major_components = cls._find_major_components(cwd)

        return cls(
            name=project_name,
            purpose=purpose,
            project_type=workspace_state.project_type,
            languages=workspace_state.languages,
            package_manager=workspace_state.package_manager,
            build_system=workspace_state.build_system,
            test_runner=workspace_state.test_runner,
            entry_points=entry_points,
            major_components=major_components,
            active_phase=active_phase,
            workspace_path=cwd,
        )

    @staticmethod
    def _infer_project_name(cwd: str) -> str:
        """Infer project name from directory or README."""
        project_dir = Path(cwd).resolve()

        # Try README first
        for readme in ["README.md", "README.txt", "README"]:
            readme_path = project_dir / readme
            if readme_path.exists():
                try:
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline().strip()
                        # Extract from markdown header
                        if first_line.startswith('#'):
                            name = first_line.lstrip('#').strip()
                            if name:
                                return name
                except Exception:
                    pass

        # Fall back to directory name
        return project_dir.name

    @staticmethod
    def _infer_purpose(cwd: str) -> Optional[str]:
        """Infer project purpose from README or CLAUDE.md."""
        project_dir = Path(cwd).resolve()

        # Check CLAUDE.md first
        claude_md = project_dir / "CLAUDE.md"
        if claude_md.exists():
            try:
                with open(claude_md, 'r', encoding='utf-8') as f:
                    content = f.read(500)
                    # Look for project description
                    for line in content.split('\n'):
                        if line.strip() and not line.startswith('#'):
                            return line.strip()[:200]
            except Exception:
                pass

        # Check README
        readme_path = project_dir / "README.md"
        if readme_path.exists():
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]
                    # Find first non-header line with substance
                    for line in lines:
                        stripped = line.strip()
                        if stripped and not stripped.startswith('#') and len(stripped) > 20:
                            return stripped[:200]
            except Exception:
                pass

        return None

    @staticmethod
    def _infer_phase(cwd: str) -> Optional[str]:
        """Infer current phase from PHASE files."""
        project_dir = Path(cwd).resolve()

        # Look for PHASE_*.md files
        phase_files = sorted(project_dir.glob("PHASE*.md"), reverse=True)
        if phase_files:
            # Get most recent phase file
            latest = phase_files[0].stem
            return latest.replace("PHASE_", "").replace("_", " ")

        return None

    @staticmethod
    def _find_entry_points(cwd: str, project_type: Optional[str]) -> list[str]:
        """Find likely entry points for the project."""
        project_dir = Path(cwd).resolve()
        entry_points = []

        # Common entry point names
        candidates = [
            "main.py", "app.py", "server.py", "index.py", "__main__.py",
            "main.rs", "lib.rs",
            "index.js", "index.ts", "app.js", "server.js",
            "Main.java", "App.java",
            "main.go",
        ]

        for candidate in candidates:
            if (project_dir / candidate).exists():
                entry_points.append(candidate)

        return entry_points

    @staticmethod
    def _find_major_components(cwd: str) -> list[str]:
        """Find major components/modules in the project."""
        project_dir = Path(cwd).resolve()
        components = []

        # Check if directory exists
        if not project_dir.exists():
            return components

        # Look for top-level directories with code
        try:
            for item in project_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.') and item.name not in {
                    "node_modules", "venv", ".venv", "target", "build", "dist",
                    "__pycache__", "tests", "test", "docs", "doc"
                }:
                    # Check if it has code files
                    has_code = any(
                        item.glob("*.py") or item.glob("*.rs") or
                        item.glob("*.js") or item.glob("*.ts") or
                        item.glob("*.java") or item.glob("*.go")
                    )
                    if has_code:
                        components.append(item.name)
        except (OSError, PermissionError):
            pass

        return components[:10]  # Limit to top 10

    def to_prompt_context(self) -> str:
        """Format as context string for LLM prompts."""
        parts = [f"Project: {self.name}"]

        if self.purpose:
            parts.append(f"Purpose: {self.purpose}")

        if self.active_phase:
            parts.append(f"Current Phase: {self.active_phase}")

        if self.project_type:
            parts.append(f"Type: {self.project_type}")

        if self.languages:
            parts.append(f"Languages: {', '.join(self.languages)}")

        if self.major_components:
            parts.append(f"Major Components: {', '.join(self.major_components)}")

        if self.entry_points:
            parts.append(f"Entry Points: {', '.join(self.entry_points)}")

        return "\n".join(parts)
