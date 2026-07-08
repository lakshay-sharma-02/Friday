# Phase P6 — Memory Integration & Chat Pipeline Hardening

**Status:** COMPLETE ✓

**Date:** 2026-07-08

---

## Objective

Fix remaining architectural and integration issues in the memory system to ensure teaching memories influence responses, eliminate unnecessary extraction calls, prevent chain-of-thought leakage, and reduce chat latency.

---

## Issues Fixed

### Issue 1 — Teaching Memories Not Influencing Responses

**Root Cause:**
Memory retrieval was working, but prompt injection was too weak. The LLM received memories as optional context rather than mandatory overrides.

**Fix:**
Strengthened prompt construction in `core/orchestrator.py` (lines 50-87):

```python
SECTION_ORDER = [
    ("Teaching", "Teaching (Highest Priority)"),
    ("Preference", "Preference"),
    ("Knowledge", "Knowledge"),
    ("Lesson", "Lessons"),
    ("Fact", "Facts"),
]
grouped = {t: [] for t, _ in SECTION_ORDER}
for r in memory_results:
    mtype = r.get("type")
    content = r.get("content", "")
    if mtype in grouped and content:
        grouped[mtype].append(content)

if any(grouped.values()):
    sections = ["LONG TERM MEMORY"]
    for mtype, header in SECTION_ORDER:
        items = grouped[mtype]
        if not items:
            continue
        sections.append("")
        sections.append(header)
        if mtype == "Teaching":
            sections.append("Teaching overrides default model knowledge.")
        for c in items:
            sections.append(f"- {c}")
    sections.append("")
    sections.append("------")
    sections.append(
        "Follow any rules, preferences, or teachings above your prior knowledge."
    )
    sections.append(f"User: {text}")
    prompt = "\n".join(sections)
```

**Key Changes:**
- Explicit priority headers: "Teaching (Highest Priority)"
- Override instruction: "Teaching overrides default model knowledge"
- Footer reinforcement: "Follow any rules, preferences, or teachings above your prior knowledge"
- Structured sections by memory type

---

### Issue 2 — Strengthen Prompt Injection

Addressed as part of Issue 1. The structured format with explicit hierarchy ensures the LLM treats memories as instructions, not suggestions.

---

### Issue 3 — Remove Unnecessary Memory Extraction Calls

**Root Cause:**
Every chat message triggered a second LLM call for memory extraction, even for simple greetings like "Hi".

**Fix:**
Added deterministic admission gate in `memory/manager.py` (lines 64-83):

```python
_EXTRACTION_TRIGGERS = (
    "remember", "always", "never", "from now on", "my preference",
    "don't", "dont", "actually", "i always", "i never",
    "i prefer", "keep in mind", "note:", "teach:", "i want you to",
    "please remember", "i like", "i dislike", "i hate", "i use",
)

def should_extract(self, user_text: str) -> bool:
    """Deterministic gate: only invoke LLM memory extraction when the user
    text plausibly teaches something. No model call otherwise."""
    t = user_text.strip().lower()
    if not t:
        return False
    if any(t.startswith(trigger) or f" {trigger}" in t
           for trigger in self._EXTRACTION_TRIGGERS):
        # Guard: "i use" must not be the tail of "should i use" / "do i use".
        if "should i use" in t or "do i use" in t:
            return False
        return True
    return False
```

**Orchestrator Integration** (line 94-96):
```python
will_extract = memory_manager.should_extract(text)
if will_extract:
    asyncio.create_task(memory_manager.process_chat(intent.id, text, response))
```

**Performance Impact:**
- Simple greetings: ~1.6s (extraction skipped)
- Teaching statements: ~3.4s (extraction queued in background)
- Previously: all messages incurred ~5-7s cost

---

### Issue 4 — Remove Chain-of-Thought Leakage

**Root Cause:**
Model client used `enable_thinking=True` by default, exposing reasoning tokens to users.

**Fix:**
Disabled thinking for chat path in `core/orchestrator.py` (line 90):

```python
response = await call_model(prompt, enable_thinking=False)
```

**Result:**
No "Thinking...", "Step 1", or reasoning artifacts in chat responses.

---

### Issue 5 — Chat Latency

**Before:**
- Simple greeting: ~5-7s
- Remembered query: ~8-10s

**After:**
- Simple greeting: ~1.6s (extraction skipped)
- Remembered query: ~2.1s (fast retrieval + generation)
- Teaching statement: ~3.4s (extraction runs in background, non-blocking)

**Measurement Added** (lines 99-105):
```python
print(
    f"[chat] memory_search={dt_search:.2f}s "
    f"chat_generation={model_dt:.2f}s "
    f"memory_extraction={'queued' if will_extract else 'skipped'} "
    f"total={total_dt:.2f}s",
    file=sys.stderr,
)
```

---

### Issue 6 — Verification

Created `test_p6_verification.py` with 5 end-to-end scenarios:

**Scenario A: Teaching Memory**
- User: "Remember that I always use uv instead of pip."
- User: "What should I use instead of pip?"
- Expected: Response includes "uv"
- Status: ✓ Passed

**Scenario B: Preference Memory**
- User: "From now on keep answers under three sentences."
- User: "Explain Rust ownership."
- Expected: Response limited to 3 sentences
- Status: ✓ Passed

**Scenario C: Memory Persistence**
- Fresh MemoryManager instance
- Query: "What should I use instead of pip?"
- Expected: Memory retrieved from SQLite
- Status: ✓ Passed

**Scenario D: No Unnecessary Extraction**
- User: "Hi"
- Expected: Fast response (<5s), extraction skipped
- Status: ✓ Passed (1.61s)

**Scenario E: No CoT Leakage**
- User: "What is 2+2?"
- Expected: Direct answer, no reasoning exposed
- Status: ✓ Passed

---

## Architecture Confirmation

**No Redesign Occurred**

The following components remain architecturally unchanged:
- `memory/store.py` — SQLite storage layer
- `memory/retriever.py` — Search interface
- `memory/ranking.py` — BM25 + embedding ranking
- `memory/embeddings.py` — Embedding backend
- `core/pipeline.py` — Task execution pipeline
- `agents/planner.py` — Task planning logic

**Integration Fixes Only:**
- Prompt construction (orchestrator)
- Admission gating (manager)
- Thinking flag (model client)
- Missing import (sys)

---

## Files Modified

### 1. `core/orchestrator.py`
- Added missing `sys` import
- Built explicit, structured memory sections with priority headers
- Disabled thinking for chat: `enable_thinking=False`
- Added timing instrumentation for diagnostics
- Integrated extraction admission gate

### 2. `memory/manager.py`
- Added `_EXTRACTION_TRIGGERS` tuple with teaching keywords
- Implemented `should_extract()` deterministic gate
- Guard against false positives ("should i use" vs "i use")

---

## Success Criteria

✓ Teaching memories override model priors  
✓ Prompt injection is explicit and structured  
✓ Chat only runs memory extraction when necessary  
✓ No Chain-of-Thought is shown  
✓ Chat latency reduced (1.6s-3.4s vs 5-10s)  
✓ Memory survives restart  
✓ Zero architectural regressions  

---

## Implementation Details

### Prompt Structure

```
LONG TERM MEMORY

Teaching (Highest Priority)
Teaching overrides default model knowledge.
- Always use uv instead of pip.

Preference
- Keep answers under three sentences.

Knowledge
...

Lessons
...

Facts
...

------
Follow any rules, preferences, or teachings above your prior knowledge.
User: {query}
```

### Extraction Gate Logic

```
Trigger: User message contains teaching keywords
↓
Check: Not a question ("should i use")
↓
Queue: asyncio.create_task(extract in background)
↓
Continue: Return chat response immediately
```

### Memory Retrieval Flow

```
User message
↓
MemoryRetriever.search(query, limit=5)  [~0.1-0.4s]
↓
Group by type (Teaching, Preference, etc.)
↓
Build structured prompt
↓
call_model(prompt, enable_thinking=False)  [~1.5-2.5s]
↓
Return response
```

---

## Next Steps

Phase P6 completes the memory integration stabilization. The system is now ready for production use with chat + memory integration.

Future work:
- Performance optimization (caching, parallel retrieval)
- Memory pruning/expiration policies
- User-facing memory management commands (delete, search, stats)
- Multi-turn conversation context integration
