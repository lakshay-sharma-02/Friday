"""P6 stabilization verification — drives the real chat path + live model proxy.

Scenarios:
  A: teaching memory overrides model prior (one bounded chat)
  D: deterministic extraction gate (pure, no model)
  E: chain-of-thought never shown (enable_thinking=False -> 0 reasoning tokens)
"""

import asyncio
import sys

sys.path.insert(0, ".")

from memory import initialize_memory_subsystem, MemoryStore, MemoryManager
from core.model_client import call_model

initialize_memory_subsystem()


async def chat_once(user_text):
    """Run a single chat turn through the real orchestrator, bounded."""
    from core.bus import EventBus
    from core.intent import Intent
    from core.orchestrator import Orchestrator

    bus = EventBus()
    orch = Orchestrator(bus)
    loop = asyncio.get_event_loop()
    orch_task = asyncio.create_task(orch.run())
    try:
        intent = Intent(kind="chat", payload={"text": user_text},
                        response_future=loop.create_future())
        await bus.publish(intent)
        return await asyncio.wait_for(intent.response_future, timeout=60)
    finally:
        orch_task.cancel()


async def main():
    store = MemoryStore()
    present = any("uv" in m["content"].lower()
                  for m in store.get_memories({"type": "Teaching"}))
    if not present:
        store.store_memory(memory_type="Teaching",
                           content="User always uses uv instead of pip.",
                           importance=0.8, source="taught", run_id="p6_A")

    # Scenario A
    a = await chat_once("What should I use instead of pip?")
    print(f"[A] response={a!r}")
    print(f"[A] uv_in_response={('uv' in a.lower())}")

    # Scenario D (pure, no model)
    mm = MemoryManager()
    print(f"[D] hi={mm.should_extract('Hi')}")
    print(f"[D] thanks={mm.should_extract('Thanks')}")
    print(f"[D] remember={mm.should_extract('Remember that I like tea.')}")
    print(f"[D] should_i_use={mm.should_extract('What should I use instead of pip?')}")

    # Scenario E (no CoT via raw probe)
    import httpx, yaml
    cfg = yaml.safe_load(open("config/models.yaml"))
    r = cfg["routes"]["cheap_chat"]
    async with httpx.AsyncClient() as c:
        pr = await c.post(
            f"{r['base_url'].rstrip('/')}/chat/completions",
            json={"model": r["model"],
                  "messages": [{"role": "user",
                                "content": "What is 2+2? One sentence."}],
                  "stream": False, "enable_thinking": False},
            headers={"Authorization": f"Bearer {r['api_key']}"})
        j = pr.json()
        rt = j["usage"]["prompt_tokens_details"].get("reasoning_tokens", 0)
        print(f"[E] reasoning_tokens_with_thinking_off={rt}")


if __name__ == "__main__":
    asyncio.run(main())
