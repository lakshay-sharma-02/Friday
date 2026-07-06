"""Environment state structure for Friday runtime."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class EnvironmentState:
    cwd: str
    workspace: dict
    computer: dict
    network: dict
    developer: dict
    operating_system: dict
    observed_at: datetime
