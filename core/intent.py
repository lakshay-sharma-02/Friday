"""Intent: the universal request unit that flows through Friday's event bus."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class Intent:
    """A request flowing through the Friday system, from any source to any handler."""

    payload: dict
    id: str = field(default_factory=lambda: str(uuid4()))
    source: str = "user"
    kind: str = "chat"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    permission_ceiling: str = "2"  # "0"=read-only, "1"=prompt, "2"=unrestricted
    response_future: asyncio.Future = field(
        default=None,
        compare=False,
        repr=False
    )

    def __post_init__(self):
        """Ensure response_future is initialized if not provided."""
        if self.response_future is None:
            try:
                loop = asyncio.get_event_loop()
                self.response_future = loop.create_future()
            except RuntimeError:
                # No event loop yet, will be set later
                pass
