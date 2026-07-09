import asyncio
import time
from core.intent import Intent
from core.orchestrator import Orchestrator
from core.bus import EventBus
import sys

async def main():
    bus = EventBus()
    orchestrator = Orchestrator(bus)
    
    # We just run one task and stop
    t0 = time.perf_counter()
    intent = Intent(
        source="cli",
        kind="task",
        payload={"text": "Read SYSTEM_ARCHITECTURE.md"}
    )
    
    # Run the orchestrator loop as a background task
    task = asyncio.create_task(orchestrator.run())
    
    # Submit the intent
    await bus.publish(intent)
    
    # Wait for the future to complete
    resp = await intent.response_future
    t1 = time.perf_counter()
    
    print(f"\nFinal response: {resp}")
    print(f"Total time elapsed: {t1 - t0:.2f}s")
    
    task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
