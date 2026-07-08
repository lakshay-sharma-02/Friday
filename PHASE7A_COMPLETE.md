# Phase 7A Complete: Memory Retrieval Framework

## Architecture
The Memory subsystem has been refactored from a monolithic implementation to a layered architecture, introducing clean separation of concerns according to the specification.

The architecture now looks like:
Memory
│
├── MemoryStore
├── MemoryRetriever
└── Ranking

- **MemoryStore**: Exclusively handles SQLite interactions, persistence, schema mapping, and CRUD operations on the unified `memories` table. It no longer ranks or applies TF-IDF logic.
- **MemoryRetriever**: Acts as the orchestrator for retrieval. It requests candidates from `MemoryStore` and delegates ranking to the `Ranking` component.
- **Ranking**: A standalone strategy containing the deterministic TF-IDF logic, fully decoupled from SQLite storage and the pipeline.

## Files Modified
- `memory/schema.sql`: Refactored to define the unified `memories` table featuring the unified memory taxonomy (Fact, Lesson, Preference, Knowledge, Teaching, Episodic).
- `memory/store.py`: Rewritten to serve exclusively as a persistence layer. Includes backward compatibility shims (`put_run`, `add_note`, `search`) that marshal legacy types and queries to the new schema and retriever.
- `memory/importance.py`: Refactored to interface with the new `importance` (REAL) and `reinforcement_count` schema rather than the old tier strings.
- `memory/__init__.py`: Updated module exports to expose `MemoryRetriever`.
- `memory/search.py`: Deleted and logic migrated to `memory/ranking.py`.

## New Abstractions
- `MemoryRetriever` (`memory/retriever.py`): New entrypoint for semantic-style retrieval, completely agnostic to how data is stored.
- `rank` strategy (`memory/ranking.py`): Extracting the TF-IDF logic makes ranking an injectable strategy.

## Why They Exist
The original memory system was tightly coupled: the SQLite store was directly executing TF-IDF calculations internally, locking the system into string-based tokens. To support vector embeddings and semantic search (Phase 7B), the storage of memories (`MemoryStore`) must be abstracted away from the search logic (`MemoryRetriever` and `Ranking`). The unified taxonomy (`type`, `content`, `importance`) ensures a standardized schema for all memories going forward. 

## Future Extension Points
- **Semantic Search (Phase 7B)**: The `Ranking` layer can easily be swapped or augmented with a vector database or embedding-based cosine similarity without modifying `MemoryStore` or `MemoryRetriever`.
- **Memory Deduplication**: The retriever can now insert a deduplication step after candidates are fetched, before ranking.
- **Pipeline Integration**: While shims currently map pipeline calls, the system is fully primed for future phases to swap legacy pipeline memory calls directly to `MemoryRetriever`.

## Regression Verification
All tests from Phase 5 and Phase 6 were executed to verify backward compatibility. Shims implemented in `MemoryStore` ensure that `put_run` correctly translates to `Episodic` memories, while `add_note` correctly maps to `Lesson` and `Teaching` types, and `store.search` translates modern output formats into the legacy schema.
