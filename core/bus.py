"""EventBus: the transport layer connecting all Friday components."""

import asyncio
from .intent import Intent


class EventBus:
    """Simple FIFO queue for passing Intents between components."""

    def __init__(self):
        self._queue: asyncio.Queue[Intent] = asyncio.Queue()

    async def publish(self, intent: Intent) -> None:
        """Push an Intent onto the bus."""
        await self._queue.put(intent)

    async def consume(self) -> Intent:
        """Pull the next Intent from the bus."""
        return await self._queue.get()
