#!/usr/bin/env python3
"""Phase 6 complete test suite - End to End system integration."""

import asyncio
import os
import time
from core.bus import EventBus
from core.intent import Intent
from core.router import route_intent
from core.orchestrator import Orchestrator

async def test_request(bus, user_input):
    print(f"\n" + "="*50)
    print(f"Testing Request: {user_input}")
    print("="*50)
    
    # Measure Routing latency
    t0 = time.perf_counter()
    intent_kind = route_intent(user_input)
    t1 = time.perf_counter()
    print(f"Routed as: {intent_kind.upper()} (Latency: {t1 - t0:.4f}s)")
    
    intent = Intent(
        kind=intent_kind,
        payload={"text": user_input},
        response_future=asyncio.get_running_loop().create_future()
    )
    
    # Measure Execution latency
    await bus.publish(intent)
    
    response = await intent.response_future
    t2 = time.perf_counter()
    
    print(f"\nResponse:\n{response}")
    print(f"\nExecution Latency: {t2 - t1:.4f}s")
    print(f"Total Latency: {t2 - t0:.4f}s")
    
    return response, intent

async def main():
    print("Starting Friday Phase 6 Integration Test Suite...")
    
    # Ensure memory and event bus are operational
    bus = EventBus()
    orchestrator = Orchestrator(bus)
    
    orch_task = asyncio.create_task(orchestrator.run())
    
    try:
        # Filesystem
        await test_request(bus, "List all markdown files in the current directory")
        await test_request(bus, "Read CLAUDE.md")
        await test_request(bus, "Search for TODO")
        
        # Shell
        await test_request(bus, "Run pytest test_http_tools.py")
        
        # Git
        await test_request(bus, "Show git status")
        
        # HTTP
        await test_request(bus, "Call the JSON API https://jsonplaceholder.typicode.com/todos/1")
        
        # Error handling tests
        await test_request(bus, "Read the file /root/super_secret_file.txt")
        await test_request(bus, "Download a file from http://localhost:9999/invalid")
        await test_request(bus, "Run an invalid shell command that doesn't exist like zzzzqqqq")
        
    finally:
        orch_task.cancel()
        try:
            await orch_task
        except asyncio.CancelledError:
            pass
        print("\nAll integration tests complete.")

if __name__ == "__main__":
    asyncio.run(main())
