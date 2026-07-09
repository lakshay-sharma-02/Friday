import asyncio
import time
from core.bus import EventBus
from core.intent import Intent
from core.orchestrator import Orchestrator
from memory import MemoryStore, initialize_memory_subsystem

async def run_chat(bus, text):
    intent = Intent(
        kind="chat",
        payload={"text": text},
        response_future=asyncio.get_event_loop().create_future()
    )
    await bus.publish(intent)
    response = await intent.response_future
    print(f"User: {text}")
    print(f"Friday: {response}\n")
    # Sleep longer for memories that are setting a preference
    if "Remember" in text or "preferred" in text or "Don't" in text:
        print("Waiting 15 seconds for background memory extraction...")
        await asyncio.sleep(15)
    else:
        await asyncio.sleep(2)

async def test_acceptance():
    initialize_memory_subsystem()
    bus = EventBus()
    orchestrator = Orchestrator(bus)
    orch_task = asyncio.create_task(orchestrator.run())
    
    print("=== ACCEPTANCE TESTS ===")
    
    # Test 1
    await run_chat(bus, "Remember: always use uv instead of pip.")
    await run_chat(bus, "What should we use instead of pip?")
    
    # Test 2
    await run_chat(bus, "My preferred compiler is clang.")
    await run_chat(bus, "What compiler do I use?")
    
    # Test 3
    await run_chat(bus, "Don't explain Git basics.")
    await run_chat(bus, "Explain git fetch.")
    
    orch_task.cancel()
    
if __name__ == "__main__":
    # Clean db for test isolation if needed, but the prompt says "Long-term memory must persist"
    # we'll just run it
    asyncio.run(test_acceptance())
