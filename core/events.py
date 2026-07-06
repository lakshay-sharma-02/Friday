"""Observation events - meaningful changes detected by observers."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Types of observation events."""
    WORKSPACE_CHANGED = "workspace_changed"
    GIT_STATE_CHANGED = "git_state_changed"
    PROCESS_STARTED = "process_started"
    PROCESS_FINISHED = "process_finished"
    COMPUTER_HEALTH_CHANGED = "computer_health_changed"
    NETWORK_CHANGED = "network_changed"
    RUNTIME_CHANGED = "runtime_changed"


@dataclass
class ObservationEvent:
    """A meaningful change detected by observers."""
    type: EventType
    timestamp: datetime
    description: str
    details: dict[str, Any]

    @classmethod
    def workspace_changed(cls, reason: str, details: dict = None) -> "ObservationEvent":
        """Create a workspace changed event."""
        return cls(
            type=EventType.WORKSPACE_CHANGED,
            timestamp=datetime.now(),
            description=reason,
            details=details or {},
        )

    @classmethod
    def git_state_changed(cls, reason: str, details: dict = None) -> "ObservationEvent":
        """Create a git state changed event."""
        return cls(
            type=EventType.GIT_STATE_CHANGED,
            timestamp=datetime.now(),
            description=reason,
            details=details or {},
        )

    @classmethod
    def process_started(cls, pid: int, command: str) -> "ObservationEvent":
        """Create a process started event."""
        return cls(
            type=EventType.PROCESS_STARTED,
            timestamp=datetime.now(),
            description=f"Process {pid} started",
            details={"pid": pid, "command": command},
        )

    @classmethod
    def process_finished(cls, pid: int, exit_code: int) -> "ObservationEvent":
        """Create a process finished event."""
        return cls(
            type=EventType.PROCESS_FINISHED,
            timestamp=datetime.now(),
            description=f"Process {pid} finished with exit code {exit_code}",
            details={"pid": pid, "exit_code": exit_code},
        )

    @classmethod
    def health_changed(cls, old_level: str, new_level: str, reasons: list[str]) -> "ObservationEvent":
        """Create a health changed event."""
        return cls(
            type=EventType.COMPUTER_HEALTH_CHANGED,
            timestamp=datetime.now(),
            description=f"Health: {old_level} → {new_level}",
            details={"old_level": old_level, "new_level": new_level, "reasons": reasons},
        )

    @classmethod
    def network_changed(cls, internet_reachable: bool) -> "ObservationEvent":
        """Create a network changed event."""
        status = "connected" if internet_reachable else "disconnected"
        return cls(
            type=EventType.NETWORK_CHANGED,
            timestamp=datetime.now(),
            description=f"Internet {status}",
            details={"internet_reachable": internet_reachable},
        )

    @classmethod
    def runtime_changed(cls, field: str, old_value: Any, new_value: Any) -> "ObservationEvent":
        """Create a runtime changed event."""
        return cls(
            type=EventType.RUNTIME_CHANGED,
            timestamp=datetime.now(),
            description=f"Runtime: {field} changed",
            details={"field": field, "old_value": old_value, "new_value": new_value},
        )


@dataclass
class EventLog:
    """Collection of observation events."""
    events: list[ObservationEvent]
    max_events: int = 50

    def __init__(self, max_events: int = 50):
        """Initialize event log."""
        self.events = []
        self.max_events = max_events

    def add(self, event: ObservationEvent) -> None:
        """Add an event to the log."""
        self.events.append(event)

        # Keep only most recent events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def recent(self, count: int = 10) -> list[ObservationEvent]:
        """Get most recent events."""
        return self.events[-count:]

    def by_type(self, event_type: EventType) -> list[ObservationEvent]:
        """Get events of a specific type."""
        return [e for e in self.events if e.type == event_type]

    def clear(self) -> None:
        """Clear all events."""
        self.events.clear()
