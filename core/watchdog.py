"""Execution watchdog - monitors long-running tool execution."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExecutionStatus(Enum):
    """Status of a monitored execution."""
    HEALTHY = "healthy"
    STALLED = "stalled"
    TIMEOUT = "timeout"


@dataclass
class WatchdogState:
    """State of an execution being monitored."""
    tool_name: str
    started_at: float
    last_output_at: float
    last_cpu_check_at: float
    output_lines: int = 0
    cpu_active: bool = True
    status: ExecutionStatus = ExecutionStatus.HEALTHY

    @property
    def elapsed_seconds(self) -> float:
        """Time since execution started."""
        return time.time() - self.started_at

    @property
    def seconds_since_output(self) -> float:
        """Time since last output."""
        return time.time() - self.last_output_at

    @property
    def seconds_since_cpu_check(self) -> float:
        """Time since last CPU activity check."""
        return time.time() - self.last_cpu_check_at


class ExecutionWatchdog:
    """Monitors long-running tool execution for stalls."""

    def __init__(self):
        """Initialize watchdog."""
        self.monitored: dict[str, WatchdogState] = {}

    def start_monitoring(self, tool_name: str, identifier: str = "default") -> None:
        """Start monitoring a tool execution.

        Args:
            tool_name: Name of the tool being executed
            identifier: Unique identifier for this execution
        """
        now = time.time()
        self.monitored[identifier] = WatchdogState(
            tool_name=tool_name,
            started_at=now,
            last_output_at=now,
            last_cpu_check_at=now,
        )

    def record_output(self, identifier: str = "default") -> None:
        """Record that output was produced.

        Args:
            identifier: Unique identifier for this execution
        """
        if identifier in self.monitored:
            state = self.monitored[identifier]
            state.last_output_at = time.time()
            state.output_lines += 1

    def record_cpu_activity(self, active: bool, identifier: str = "default") -> None:
        """Record CPU activity status.

        Args:
            active: Whether CPU activity was detected
            identifier: Unique identifier for this execution
        """
        if identifier in self.monitored:
            state = self.monitored[identifier]
            state.cpu_active = active
            state.last_cpu_check_at = time.time()

    def check_health(self, identifier: str = "default") -> Optional[WatchdogState]:
        """Check health of a monitored execution.

        Returns:
            WatchdogState if being monitored, None otherwise
        """
        if identifier not in self.monitored:
            return None

        state = self.monitored[identifier]

        # Check for stall conditions
        no_output = state.seconds_since_output > 120  # 2 minutes without output
        no_cpu = not state.cpu_active
        long_running = state.elapsed_seconds > 180  # 3 minutes total

        if no_output and no_cpu and long_running:
            state.status = ExecutionStatus.STALLED

        # Check for timeout (never silently wait forever)
        if state.elapsed_seconds > 600:  # 10 minutes absolute max
            state.status = ExecutionStatus.TIMEOUT

        return state

    def stop_monitoring(self, identifier: str = "default") -> Optional[WatchdogState]:
        """Stop monitoring an execution.

        Args:
            identifier: Unique identifier for this execution

        Returns:
            Final WatchdogState if it was being monitored, None otherwise
        """
        return self.monitored.pop(identifier, None)

    def get_state(self, identifier: str = "default") -> Optional[WatchdogState]:
        """Get current state of a monitored execution.

        Args:
            identifier: Unique identifier for this execution

        Returns:
            WatchdogState if being monitored, None otherwise
        """
        return self.monitored.get(identifier)
