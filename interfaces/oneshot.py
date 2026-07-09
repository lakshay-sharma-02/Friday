"""One-shot command execution for Friday."""

import asyncio
from core.bus import EventBus
from core.intent import Intent
from core.router import route_intent


async def run_oneshot(bus: EventBus, command: str) -> None:
    """Execute a single command and exit."""

    loop = asyncio.get_event_loop()

    # Route the command
    intent_kind = route_intent(command)

    intent = Intent(
        kind=intent_kind,
        payload={"text": command},
        response_future=loop.create_future()
    )

    # Publish to bus
    await bus.publish(intent)

    # Wait for response
    response = await intent.response_future

    # Print response
    print(response)
