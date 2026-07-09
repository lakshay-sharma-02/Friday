import asyncio
import time
from core.bus import EventBus
from core.intent import Intent
from core.orchestrator import Orchestrator
from memory import MemoryStore
from core.pipeline import run_pipeline

async def run_audit():
    bus = EventBus()
    orchestrator = Orchestrator(bus)
    
    # Run orchestrator in background
    orch_task = asyncio.create_task(orchestrator.run())
    
    print("\n--- TEST 1: The 'Remember:' Command ---")
    intent = Intent(
        kind="chat", # Router maps "Remember: always use uv" to chat
        payload={"text": "Remember: always use uv instead of pip in this project."},
        response_future=asyncio.get_event_loop().create_future()
    )
    await bus.publish(intent)
    response = await intent.response_future
    print(f"Friday response: {response}")
    
    print("\n--- TEST 2: Memory Retrieval for Chat ---")
    intent2 = Intent(
        kind="chat",
        payload={"text": "What did I teach you about uv and pip?"},
        response_future=asyncio.get_event_loop().create_future()
    )
    await bus.publish(intent2)
    response2 = await intent2.response_future
    print(f"Friday response: {response2}")
    
    orch_task.cancel()
    
    print("\n--- TEST 3: Direct Memory Check ---")
    store = MemoryStore()
    notes = store.get_all_notes()
    print(f"Total Notes in SQLite: {len(notes)}")
    for n in notes:
        print(f"Note: {n}")
        
if __name__ == "__main__":
    asyncio.run(run_audit())
