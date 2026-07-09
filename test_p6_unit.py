"""P6 unit verification: chat prompt injection (Issues 1/2) + gate (3) + CoT (4)."""

import asyncio
import re
import sys

sys.path.insert(0, ".")

from memory import initialize_memory_subsystem, MemoryStore
from core.model_client import call_model

initialize_memory_subsystem()

SECTION_ORDER = [
    ("Teaching", "Teaching (Highest Priority)"),
    ("Preference", "Preference"),
    ("Knowledge", "Knowledge"),
    ("Lesson", "Lessons"),
    ("Fact", "Facts"),
]


async def chat(user_text):
    from memory.manager import MemoryManager
    mm = MemoryManager()
    results = mm.search(user_text, limit=5)
    grouped = {t: [] for t, _ in SECTION_ORDER}
    for r in results:
        if r.get("type") in grouped and r.get("content"):
            grouped[r["type"]].append(r["content"])
    prompt = user_text
    if any(grouped.values()):
        sections = ["LONG TERM MEMORY"]
        for mtype, header in SECTION_ORDER:
            items = grouped[mtype]
            if not items:
                continue
            sections += ["", header]
            if mtype == "Teaching":
                sections.append("Teaching overrides default model knowledge.")
            sections += [f"- {c}" for c in items]
        sections += ["", "------",
                     "Follow any rules, preferences, or teachings above your prior knowledge.",
                     f"User: {user_text}"]
        prompt = "\n".join(sections)
    return await call_model(prompt, enable_thinking=False), prompt


def count_sentences(t):
    return len([s for s in re.split(r'(?<=[.!?])\s+', t.strip()) if s.strip()])


async def main():
    store = MemoryStore()
    if not any("uv" in m["content"].lower() for m in store.get_memories({"type": "Teaching"})):
        store.store_memory(memory_type="Teaching", content="User always uses uv instead of pip.",
                           importance=0.8, source="taught", run_id="p6_A")
    if not any("three sentences" in m["content"].lower() for m in store.get_memories({"type": "Preference"})):
        store.store_memory(memory_type="Preference", content="Keep answers under three sentences.",
                           importance=0.8, source="taught", run_id="p6_B")

    # Scenario A
    a_resp, a_prompt = await chat("What should I use instead of pip?")
    print("[A] uv_followed =", "uv" in a_resp.lower())
    print("[A] prompt_has_teaching =", "User always uses uv instead of pip." in a_prompt)
    print("[A] prompt_has_override =", "Teaching overrides default model knowledge." in a_prompt)
    print("[A] response =", repr(a_resp))

    # Scenario B
    b_resp, _ = await chat("Explain Rust ownership.")
    n = count_sentences(b_resp)
    print("[B] sentences =", n, "| <=3:", n <= 3)
    print("[B] response =", repr(b_resp))

    # Scenario D (gate, pure)
    from memory.manager import MemoryManager
    mm = MemoryManager()
    print("[D] hi =", mm.should_extract("Hi"))
    print("[D] thanks =", mm.should_extract("Thanks"))
    print("[D] remember =", mm.should_extract("Remember that I like tea."))
    print("[D] what_should_i_use =", mm.should_extract("What should I use instead of pip?"))

    # Scenario E (CoT off -> 0 reasoning tokens)
    import httpx, yaml
    cfg = yaml.safe_load(open("config/models.yaml"))
    r = cfg["routes"]["cheap_chat"]
    async with httpx.AsyncClient() as c:
        pr = await c.post(
            f"{r['base_url'].rstrip('/')}/chat/completions",
            json={"model": r["model"],
                  "messages": [{"role": "user", "content": "What is 2+2? One sentence."}],
                  "stream": False, "enable_thinking": False},
            headers={"Authorization": f"Bearer {r['api_key']}"})
        rt = pr.json()["usage"]["prompt_tokens_details"].get("reasoning_tokens", 0)
        print("[E] reasoning_tokens_with_thinking_off =", rt)


if __name__ == "__main__":
    asyncio.run(main())
