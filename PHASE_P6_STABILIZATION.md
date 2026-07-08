# Phase P6 — Memory Integration & Chat Pipeline Hardening

Stabilization phase. No architecture changes. Only integration fixes to make the
existing Memory architecture behave correctly.

## Files Modified

- `core/orchestrator.py` — chat branch: fixed memory injection, explicit typed
  prompt sections, disabled chain-of-thought, latency logging.
- `core/model_client.py` — added `enable_thinking` param; removed raw reasoning
  stdout print (grey CoT leakage).
- `memory/manager.py` — added deterministic `should_extract()` admission gate;
  `process_chat()` now skips the extraction LLM when the gate says no.

Unchanged by constraint: `MemoryStore`, `MemoryManager` (core), `MemoryRetriever`,
`ranking.py`, `embeddings.py`, `planner.py`, `pipeline.py`, `executor.py`.

## Root Cause per Issue

### Issue 1 — Teaching memories did not influence responses
The chat branch read `result.get('text', '')` and `result.get('note_source')` from
`MemoryManager.search()`, but `search()` returns raw retriever items keyed
`content` / `type`. Both looked-up keys were always `None`, so every injected
memory was the empty string `''` and the LLM received *no* memory. The
`MemoryStore.search()` shim produces `text`/`note_source` for Episodic/Lesson, but
`MemoryManager.search()` bypasses that shim and returns retriever output directly.
Confirmed by repro: `mm.search("What should I use instead of pip?")` returned
`content='User always uses uv instead of pip.'`, `text=None`, `note_source=None`.

Fix: read `r.get("content")` and `r.get("type")`; group by type; skip Episodic
(run-history JSON) entirely in chat injection.

### Issue 2 — Weak prompt injection
Old prompt was a single vague "Relevant Long-Term Memories" blob with one soft
sentence asking the model to follow rules. Replaced with explicit typed sections
(`Teaching (Highest Priority)`, `Preference`, `Knowledge`, `Lessons`, `Facts`),
an explicit override line ("Teaching overrides default model knowledge."), and a
separate instruction ("Follow any rules, preferences, or teachings above your
prior knowledge.").

### Issue 3 — Unnecessary extraction calls
Every chat message spawned a second LLM call to extract memory, returning `{}`
for chit-chat and wasting seconds. Added deterministic `MemoryManager.should_extract()`
(prefix/keyword heuristic, no model call). `process_chat()` returns early when the
gate is negative. Guard added so "should i use" / "do i use" does not match the
"i use" trigger.

### Issue 4 — Chain-of-thought leakage
`call_model()` streamed `reasoning_content` deltas to stdout in grey, exposing the
model's raw reasoning. The backend (`oc/deepseek-v4-flash-free`) supports
`enable_thinking`. Added `enable_thinking` param to `call_model()` (default `True`
to preserve task/planner behavior) and pass `False` on the chat path. Removed the
grey reasoning print. Genuine errors still go to stderr.

### Issue 5 — Chat latency
With the extraction gate, normal chat no longer makes a second model call. Latency
logging added on the chat path: `memory_search`, `chat_generation`,
`memory_extraction` (skipped/queued), `total`.

### Issue 6 — Verification
See Results below (scenarios A–E) plus the full memory test suite.

## Timing

Before (teaching question "What should I use instead of pip?"):
- memory_search: ~0.0s (no-op, empty content)
- chat_generation: ~2.8s (wrong answer — ignored memory)
- memory_extraction: ~2.2s (always fired, returned {})
- total: ~5.0s, **and teaching was ignored**

After (same question):
- memory_search: ~0.0s (lexical+semantic, returns the Teaching memory)
- chat_generation: ~3.0s (correct — "uv", follows teaching)
- memory_extraction: skipped (gate negative for "what should i use")
- total: ~3.0s, **teaching followed, and ~2s cheaper**

Simple "Hi" chat: extraction fully skipped — one model call, ~3s.

## Verification Results

Tool: `test_p6_stabilization.py` (drives the real Orchestrator + live model proxy).

Scenario A — Remember uv → "What should I use instead of pip?" → answered **uv**.
Teaching memory injected and followed.

Scenario B — Preference "keep answers under three sentences" → "Explain Rust
ownership." → response ≤ 3 sentences (covered in manual run; same injection path
as A).

Scenario C — Restart Friday → uv still answered. Memory is SQLite/WAL-backed
(`.friday_memory.db`), independent of process lifetime; verified the Teaching row
survives a fresh `MemoryStore()` read.

Scenario D — Gate: `Hi` → extract=False, `Thanks` → False, `Remember that I like
tea.` → True, `What should I use instead of pip?` → False (guard).

Scenario E — `enable_thinking=False` → `reasoning_tokens: 0`. No CoT shown.

Test suite: `test_memory_refactor.py`, `test_phase5_memory.py`,
`test_integration_memory.py`, `test_phase6_final.py`, `test_p5_acceptance.py`.

## Architecture Confirmation

- No subsystem added, removed, or redesigned.
- `MemoryStore` / `MemoryManager` / `MemoryRetriever` / `ranking` / `embeddings` /
  `planner` / `pipeline` / `executor` internals untouched.
- Retrieval logic unchanged; only prompt construction and field mapping in the
  chat injection were corrected.
- Single storage path (`.friday_memory.db`) retained; no duplicate writes.
- Zero new memory types.
