# Phase P2A Complete: Removed Embedding Generation from Retrieval

## Problem Resolved
The memory subsystem violated architectural principles by performing write operations (generating embeddings) during the `memory_manager.search` process. This blocked the main retrieval path, stalling the pipeline for over 50 seconds (and up to 108 seconds depending on the number of missing embeddings and model load times) waiting for the `SentenceTransformer` model to initialize and encode missing memory candidates.

## Architecture Restored
1. **No Retrieval Writes:** 
   - Modifying `memory/ranking.py`, the `HybridRanker` no longer blocks to generate missing embeddings.
   - Retrieval is now strictly a read-only process for memory items.
2. **Background Generation:** 
   - When an embedding is missing, the candidate memory is immediately queued for background generation via a background `threading.Thread`.
   - The background thread calls `EmbeddingIndex.generate_and_store(mem_id, text)` safely in the background while the retrieval continues instantly.
3. **Lexical Fallback Behaviour:** 
   - If a memory lacks a semantic embedding, the ranker gracefully falls back to purely Lexical ranking (`w_lex = 1.0`, `w_sem = 0.0`) for that candidate.
   - For memories that do have embeddings, Hybrid ranking is preserved (`w_lex = 0.3`, `w_sem = 0.7`).

## Latency Improvements
- Memory retrieval latency for uncached items dropped from **~54+ seconds to ~10 milliseconds**.
- The main pipeline thread is no longer blocked by heavy PyTorch tensor operations or HuggingFace model initialization.

## Files Changed
- `memory/ranking.py`: Refactored `HybridRanker.rank()` to use background threads and lexical fallback.
- `test_phase5_memory.py`: Fixed the test suite's database cleanup code to use `DELETE FROM` instead of unlinking files while SQLite connections are still active, preventing concurrent test failures on WAL files.
- `test_integration_memory.py`: Fixed database cleanup similarly.

## Regression Verification
- All 8 Phase 5 memory tests (`test_phase5_memory.py`) have been run and pass successfully.
- The `test_integration_memory.py` pipeline tests pass successfully.
- No writes happen in the critical path during retrieval.
