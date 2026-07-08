# Phase 7A.5: Memory Architecture Alignment

## Architecture Before
- `Pipeline` directly instantiated and queried `MemoryStore` (`put_run`, `add_note`, `search`).
- `Planner` (`create_plan`) manually parsed the `LESSON:` string out of the LLM response text, leaking memory logic into the planner's response formatting.
- `MemoryStore` silently accepted all pipeline runs (success or failure) and promoted every single one into `Episodic` memory.
- No separation between raw execution logs (history) and curated knowledge (memory).

## Architecture After
- `Pipeline` interacts solely with `MemoryManager`. It no longer knows about `MemoryStore` or SQLite.
- `MemoryManager` acts as the single entry point for admission, routing, and processing of both history and memories.
- `MemoryManager` performs the explicit parsing of the `LESSON:` block out of the raw `Planner` output.
- `MemoryStore` strictly handles schema insertion, updates, and persistence.
- `Episodic` memories are now protected by an admission gate. Routine, successful executions are recorded strictly to the `history` table. Only executions that fail, retry, or generate an explicit lesson are promoted to long-term `Episodic` memory.
- Schema prepared for `EmbeddingIndex` to allow vectors to be stored externally to the `memories` table without coupling the core data.

## Responsibilities Moved
- **Lesson Parsing**: Moved from `agents/planner.py` to `MemoryManager.extract_lesson()`.
- **Pipeline Insertion**: Moved from `Pipeline` -> `MemoryStore` to `Pipeline` -> `MemoryManager.process_run()`.
- **Memory Search Orchestration**: Moved from `Pipeline` -> `MemoryStore` to `Pipeline` -> `MemoryManager`.

## Responsibilities Unchanged
- **TF-IDF Ranking**: Remains strictly inside `memory/ranking.py`.
- **Retrieval Orchestration**: Remains strictly inside `MemoryRetriever`.
- **Memory Storage**: Remains strictly inside `MemoryStore`.
- **Pipeline Orchestration**: `Pipeline` still owns the execution loop, it just delegates memory to the manager.

## Files Modified
- `agents/planner.py`: Replaced manual `LESSON:` string splitting with `MemoryManager().extract_lesson()`.
- `core/pipeline.py`: Replaced `store.put_run` and `store.add_note` with `memory_manager.process_run()`. Replaced `store.search` with `memory_manager.search()`.
- `memory/manager.py`: Created new class to centralize memory admission logic and lesson parsing.
- `memory/schema.sql`: Added `history` table to store unpromoted events, and `embedding_index` table to prepare for Phase 7B.
- `memory/store.py`: Added `append_history` for raw logging, and explicitly marked compatibility shims (`put_run`, `add_note`, `search`) with `TODO(Phase 7C)`.
- `memory/__init__.py`: Exported `MemoryManager`.

## Remaining Temporary Shims
- `MemoryStore.put_run()`
- `MemoryStore.add_note()`
- `MemoryStore.search()`
- `MemoryStore.stats()`
- `MemoryStore.get_run()`
- `MemoryStore.get_all_runs()`

These shims bridge the current tests and legacy interfaces to the new `memories` table. They are marked for removal in Phase 7C after all components natively utilize `MemoryManager`.

## Future Phase 7B Integration Points
- **Embeddings**: By adding the `embedding_index` table, Phase 7B can insert vector representations without modifying the core `memories` schema. 
- **Retrieval**: Vector cosine similarity can simply be swapped into `Ranking` without affecting the `MemoryManager`, `Pipeline`, or `MemoryStore`.
