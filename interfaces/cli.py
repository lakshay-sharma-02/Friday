"""CLI: stdin-based interface for interacting with Friday."""

import asyncio
import time
import os
from core.bus import EventBus
from core.intent import Intent
from core.router import route_intent


async def run_cli(bus: EventBus) -> None:
    """Read user input, publish Intents, print responses."""

    loop = asyncio.get_event_loop()

    print("Friday CLI ready. Type 'exit' or 'quit' to stop.")
    
    verbose = os.getenv("VERBOSE") == "1" or os.getenv("VERBOSE_PIPELINE") == "1"

    while True:
        try:
            # Read input in a thread-safe way (input() blocks the event loop)
            user_input = await asyncio.to_thread(input, "> ")

            # Check for exit commands
            if user_input.strip().lower() in ("exit", "quit"):
                print("Goodbye.")
                break

            # Detect teach: prefix for explicit teaching
            if user_input.strip().startswith("teach:"):
                teach_text = user_input.strip()[6:].strip()
                from memory import MemoryStore
                store = MemoryStore()
                store.add_note(content=teach_text, source="taught", source_run_id=None)
                print(f'Got it, I\'ll remember: "{teach_text}"')
                continue

            # Detect memory:stats command
            if user_input.strip() == "memory:stats":
                from memory import MemoryStore
                store = MemoryStore()
                stats = store.stats()
                print("\n=== Memory Statistics ===")
                print(f"Total runs: {stats.get('total_runs', 0)}")
                print(f"Total notes: {stats.get('total_notes', 0)}")
                print(f"\nRuns by tier:")
                for tier, count in stats.get('runs_by_tier', {}).items():
                    print(f"  {tier}: {count}")
                print(f"\nNotes by tier:")
                for tier, count in stats.get('notes_by_tier', {}).items():
                    print(f"  {tier}: {count}")
                print(f"\nNotes by source:")
                for source, count in stats.get('notes_by_source', {}).items():
                    print(f"  {source}: {count}")
                print()
                continue

            # Detect memory:retier command
            if user_input.strip() == "memory:retier":
                from memory import MemoryStore, retier_all
                store = MemoryStore()
                moved = retier_all(store)
                print("\n=== Retiering Complete ===")
                print(f"Moved to HOT: {moved.get('HOT', 0)}")
                print(f"Moved to WARM: {moved.get('WARM', 0)}")
                print(f"Moved to COLD: {moved.get('COLD', 0)}")
                print()
                continue

            # Detect scheduler:fire_now command
            if user_input.strip() == "scheduler:fire_now":
                from triggers.scheduler import fire_now
                print("Firing scheduled task now...")
                await fire_now(bus)
                print("Scheduled task fired.")
                continue

            # Detect task: prefix
            if user_input.strip().startswith("task:"):
                task_text = user_input.strip()[5:].strip()
                intent = Intent(
                    kind="task",
                    payload={"text": task_text},
                    response_future=loop.create_future()
                )
                if verbose:
                    print("[router] classified request as TASK (forced via prefix)")
            else:
                # ROUTER: Automatic Intent Classification
                intent_kind = route_intent(user_input)
                if verbose:
                    print(f"[router] classified request as {intent_kind.upper()}")
                    
                intent = Intent(
                    kind=intent_kind,
                    payload={"text": user_input},
                    response_future=loop.create_future()
                )

            # Publish to bus
            t0 = time.perf_counter()
            await bus.publish(intent)

            # Wait for response (already streamed to stdout by call_model for chat)
            response = await intent.response_future
            total_dt = time.perf_counter() - t0

            # For task or hybrid intents, print the summary
            if intent.kind in ("task", "hybrid"):
                print(f"\n{response}")
                print(f"[{total_dt:.2f}s]")
            else:
                # Show timing breakdown if available (chat path)
                model_time = intent.metadata.get("model_time") if hasattr(intent, "metadata") and intent.metadata else None
                if model_time is not None:
                    print(f"[model: {model_time:.2f}s, total: {total_dt:.2f}s]")
                else:
                    print(f"[{total_dt:.2f}s]")

        except EOFError:
            # Reached end of piped input
            break
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break
