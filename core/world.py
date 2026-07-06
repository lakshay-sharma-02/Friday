"""World Model - Friday's single source of truth about its environment."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class WorkspaceState:
    """State of the current workspace/project."""
    cwd: str
    project_type: Optional[str] = None
    languages: list[str] = field(default_factory=list)
    build_system: Optional[str] = None
    test_runner: Optional[str] = None
    package_manager: Optional[str] = None
    top_level_files: list[str] = field(default_factory=list)

    # Git state
    is_git_repo: bool = False
    git_branch: Optional[str] = None
    git_clean: Optional[bool] = None
    git_modified_files: list[str] = field(default_factory=list)


@dataclass
class ComputerState:
    """State of the physical/virtual machine."""
    os: Optional[str] = None
    architecture: Optional[str] = None
    hostname: Optional[str] = None
    logical_cores: Optional[int] = None
    ram_gb: Optional[int] = None
    disk_total: Optional[str] = None
    disk_used: Optional[str] = None
    disk_available: Optional[str] = None
    disk_use_percent: Optional[str] = None
    gpu: Optional[str] = None
    battery_percent: Optional[str] = None
    python_version: Optional[str] = None
    current_user: Optional[str] = None


@dataclass
class NetworkState:
    """State of network connectivity."""
    internet_reachable: bool = False
    hostname: Optional[str] = None
    local_ip: Optional[str] = None
    loopback_available: bool = True
    dns_available: bool = False
    interfaces: list[str] = field(default_factory=list)


@dataclass
class DeveloperState:
    """State of available developer tools."""
    tools: dict[str, dict] = field(default_factory=dict)

    def is_available(self, tool_name: str) -> bool:
        """Check if a tool is available."""
        return self.tools.get(tool_name, {}).get("available", False)

    def get_version(self, tool_name: str) -> Optional[str]:
        """Get version of a tool if available."""
        return self.tools.get(tool_name, {}).get("version")


@dataclass
class ProcessInfo:
    """Information about a single process."""
    pid: int
    command: str
    started_at: float
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    status: str = "running"
    exit_code: Optional[int] = None


@dataclass
class ProcessState:
    """State of running processes."""
    processes: dict[int, ProcessInfo] = field(default_factory=dict)

    def add_process(self, process: ProcessInfo) -> None:
        """Add a process to tracking."""
        self.processes[process.pid] = process

    def remove_process(self, pid: int) -> Optional[ProcessInfo]:
        """Remove a process from tracking."""
        return self.processes.pop(pid, None)

    def get_process(self, pid: int) -> Optional[ProcessInfo]:
        """Get info about a specific process."""
        return self.processes.get(pid)

    def active_processes(self) -> list[ProcessInfo]:
        """Get all active processes."""
        return [p for p in self.processes.values() if p.status == "running"]


@dataclass
class RuntimeState:
    """State of Friday's own execution."""
    task_text: str = ""
    pipeline_active: bool = False
    current_step: int = 0
    total_steps: int = 0
    running_tool: Optional[str] = None
    retry_count: int = 0
    task_start_time: Optional[float] = None
    elapsed_seconds: float = 0.0
    last_observation_time: Optional[float] = None
    verbose_mode: bool = False

    def update_elapsed(self, current_time: float) -> None:
        """Update elapsed time."""
        if self.task_start_time:
            self.elapsed_seconds = current_time - self.task_start_time


@dataclass
class WorldState:
    """Friday's complete understanding of its environment.

    The single source of truth. All subsystems read from this, only observers write to it.
    """
    workspace: WorkspaceState
    computer: ComputerState
    network: NetworkState
    developer: DeveloperState
    runtime: RuntimeState
    processes: ProcessState
    observed_at: datetime

    @classmethod
    def empty(cls, cwd: str = ".") -> "WorldState":
        """Create an empty WorldState for initialization."""
        return cls(
            workspace=WorkspaceState(cwd=cwd),
            computer=ComputerState(),
            network=NetworkState(),
            developer=DeveloperState(),
            runtime=RuntimeState(),
            processes=ProcessState(),
            observed_at=datetime.now(),
        )
