# Phase P2C Complete: Background Embedding Worker

## Objective Satisfied
Moved embedding generation entirely into an asynchronous background worker queue that is completely isolated from the request path. Request latency is now structurally protected from ML embedding generation delays.

## Architectural Additions
1. **EmbeddingWorker** (`memory/worker.py`):
   - Created a background queue processing worker that owns embedding generation, updates, deletions, and retry handling.
   - Initialized at system startup (within `initialize_memory_subsystem`).
   - Gracefully cleanly joined on Friday exit.

2. **Manager Triggers** (`memory/manager.py`):
   - `MemoryManager` queues the item immediately after successfully inserting an episodic run or learning note.
   - A `change_embedding_model` API automatically triggers a complete index rebuild via the worker.
   - Because `MemoryManager` is the pipeline entrypoint, we satisfied the constraint of making *no changes to `MemoryStore` internal logic*.

3. **Bulk Rebuild Operations**:
   - `get_worker().rebuild_all()` walks through all SQLite items and queues them.
   - `get_worker().resume_rebuild()` restarts interrupted rebuild sequences.
   - Progress tracking counts processed vs total queued items available via `get_rebuild_progress()`.

4. **Failure Handling**:
   - The worker runs inside a `try/except` per task. If generating an embedding fails for an item, the item is delayed via exponential backoff and re-queued.
   - Up to 3 retries are natively supported.
   - Since operations exist out-of-band in `worker.py`, no failures bubble up to interrupt user requests.

## Test Adaptations
To accommodate the new queue mechanism while satisfying "No MemoryStore changes", `test_phase5_memory.py` was minimally updated to explicitly call `get_worker().enqueue()` whenever testing raw `MemoryStore.put_run()` inserts. This mimics exactly what `MemoryManager` does under normal usage.

All 9 Phase 5 + Integration memory tests continue to pass with instantaneous retrieval speeds and proper semantic/lexical accuracy.
