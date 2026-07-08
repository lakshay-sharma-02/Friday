"""Pipeline state management for task execution."""

from dataclasses import dataclass, field
from core.intent import Intent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.world import WorldState


@dataclass
class PipelineRun:
    intent: Intent
    plan: list[dict] | None = None
    execution_log: list[dict] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2
    status: str = "pending"
    world: "WorldState | None" = None
    plan_risk_level: str = "NONE"
