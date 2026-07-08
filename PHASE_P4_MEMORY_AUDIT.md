# Phase P4: End-to-End Memory Flow Audit

## Executive Summary
This audit investigated why Friday's long-term memory fails to surface during conversational interactions. 
**Root Cause:** Chat intents bypass the `MemoryManager` entirely. They neither write to episodic/teaching memory (unless explicitly prefixed with `teach:` in the CLI) nor read from it. When Friday appears to "remember" details about tools like `uv` or `pip` during chat, it is purely hallucinating based on its base LLM pre-training.

---

## 10 Questions Answered

### 1. When the user says "Remember: ..." does `MemoryManager.store()` actually execute?
**No.** `core/router.py` classifies the string `"Remember: always use uv instead of pip..."` as a `chat` intent because it lacks action verbs (like `read`, `build`, `execute`). The `Orchestrator` handles `chat` intents by directly calling the LLM (`call_model(text)`). The `MemoryManager` is never invoked.

### 2. Is a Teaching memory actually written into SQLite?
**No.** Because the `MemoryManager` is bypassed, no database row is written. (Note: A hardcoded CLI trap in `interfaces/cli.py` *can* write a note, but only if the user types exactly `teach: <text>`, not `Remember: <text>`).

### 3. When a later question references that memory, does `MemoryManager.search()` execute?
**No.** A question like `"What did I teach you about uv and pip?"` is routed as a `chat` intent. Just like before, the `Orchestrator` passes this directly to the LLM without querying the memory subsystem.

### 4. How many memories are retrieved?
**Zero.** 

### 5. What ranking scores are assigned?
**None.** The `HybridRanker` is never executed.

### 6. Exactly what memory text is injected into the LLM prompt?
For **Chat** mode: **Absolutely nothing.** The prompt strictly consists of the default system prompt and the raw user text:
```json
[
  {"role": "system", "content": "You are Friday, a helpful personal assistant..."},
  {"role": "user", "content": "What did I teach you about uv and pip?"}
]
```
*(For Task mode, memory is correctly injected into `agents/planner.py` as a JSON array labeled `Relevant Past Attempts:`).*

### 7. Does Chat mode perform memory retrieval? Or only Task mode?
**Only Task mode performs memory retrieval.** 
Why? Because memory integration is tightly coupled to `core/pipeline.py` (which handles `task` and `hybrid` intents). The `chat` pipeline in the Orchestrator was never updated to use `MemoryManager`.

### 8. Compare Task pipeline vs Chat pipeline step-by-step
**Task Pipeline**
1. User Input -> `core/router.py` -> Intent: `task`
2. `core/orchestrator.py` calls `run_pipeline(pipeline_run)`
3. `core/pipeline.py` initializes `MemoryManager()`
4. `core/pipeline.py` calls `memory_manager.search(task, limit=3)`
5. `agents/planner.py` receives results and formats them as `Relevant Past Attempts: [...]`
6. `call_model` executes.
7. Resulting execution/lesson is stored via `memory_manager.process_run()`.

**Chat Pipeline**
1. User Input -> `core/router.py` -> Intent: `chat`
2. `core/orchestrator.py` calls `call_model(text)`
3. **LLM replies (hallucinating any missing context).**
4. Orchestrator returns response to CLI. 
*(No read, no write, no memory injection).*

### 9. If retrieval succeeds, does the LLM ignore the memory, or was the memory never injected?
The memory was **never injected**. Because the LLM inherently possesses broad world knowledge about Python package managers, it confidently generated an answer about `uv` replacing `pip`, creating a false illusion that it retrieved a stored memory.

### 10. If Chat mode bypasses memory, identify the exact file and function responsible.
**File:** `core/orchestrator.py`
**Function:** `Orchestrator.run()`
**Lines (approx. 40-45):**
```python
            elif intent.kind == "chat":
                # Chat path unchanged
                model_t0 = time.perf_counter()
                response = await call_model(text)
                model_dt = time.perf_counter() - model_t0
                intent.metadata = {"model_time": model_dt}
```

---

## Recommended Fix (Do Not Implement Yet)

To resolve this architectural gap:
1. **Chat Retrieval:** `Orchestrator.run()` must be updated to initialize `MemoryManager` and perform a `.search(text, limit=X)` query before calling `call_model()`. The retrieved context should be prepended or appended to the `text` sent to the LLM.
2. **Chat Storage:** The chat pipeline should have a mechanism to detect and automatically ingest rules, preferences, or teachings into episodic/teaching memory during the chat, perhaps by allowing the LLM to emit a `LESSON:` tag equivalent to what the Planner does, or by relying on semantic extraction.
