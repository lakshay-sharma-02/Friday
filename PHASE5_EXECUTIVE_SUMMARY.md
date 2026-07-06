# Phase 5: Persistent Memory - COMPLETE ✅

## Status: Production Ready

Phase 5 adds persistent memory to Friday with deterministic search and importance tiering. **Core principle maintained: memory operations use TF-IDF math (no additional LLM calls beyond the existing single Planner invocation).**

---

## What Was Built

### 1. Storage (SQLite + WAL)
- Crash-durable storage via `PRAGMA journal_mode=WAL`
- Two tables: `runs` (every task execution) + `notes` (lessons + teachings)
- Every write followed by immediate commit (no batching)
- **Test 3 proves durability**: 3 runs before crash → 3 runs after crash

### 2. Search (TF-IDF - Deterministic)
- From-scratch implementation using stdlib (`collections.Counter` + `math.log`)
- Zero new dependencies (no scikit-learn)
- Corpus = all run texts + all note texts
- Returns top-k matches sorted by cosine similarity
- **Test 2 proves semantic matching**: "git status" matches "show me the git repository status"

### 3. Tiering (Formula-based)
- **HOT**: last_accessed ≤ 24h OR access_count ≥ 5
- **WARM**: last_accessed ≤ 14 days
- **COLD**: everything else
- Pure function, no LLM judgment
- **Test 4 proves aging**: 20-day-old run correctly moves HOT → COLD

### 4. Teaching (teach: prefix)
- `teach: <text>` bypasses pipeline, writes directly to storage
- No LLM call, just a database insert with source='taught'
- **Test 5+6 prove storage and retrieval**: taught notes are searchable

### 5. Lesson Extraction (same LLM call)
- Planner system prompt includes: "optionally emit `LESSON: ...` for non-obvious constraints"
- Few-shot examples calibrate the bar (workspace-specific, not trivial)
- Parsing extracts trailing `LESSON:` line, stores as note with source='lesson'
- **Test 7+8 prove extraction and calibration**: lessons stored, no spurious lessons

### 6. Planner Integration
- Memory search before planning: `store.search(task, limit=3)`
- Results passed to planner via `memory_results` parameter
- Prompt includes `relevant_past_attempts` section
- **Demonstration proves integration**: memory results appear in planner prompt

### 7. Pipeline Wiring
- Search memory at start of each run
- Store runs at end (success OR failure - failures are worth remembering)
- Store lessons if planner emitted one
- All async via `asyncio.to_thread` wrappers

### 8. CLI Commands
- `memory:stats` - print storage statistics
- `memory:retier` - trigger retiering manually

---

## All 8 Tests Pass

```
TEST 1: Two runs stored ✓
TEST 2: Semantic search (0.4627 score for exact, 0.2525 for paraphrase) ✓
TEST 3: Crash durability (3 runs survive process termination) ✓
TEST 4: Tier aging (HOT → COLD after 20 days) ✓
TEST 5: Taught notes stored (source='taught') ✓
TEST 6: Taught notes searchable (0.6325 relevance score) ✓
TEST 7: Lessons stored (source='lesson') ✓
TEST 8: No spurious lessons (trivial tasks don't emit LESSON lines) ✓
```

---

## Key Verification

**TF-IDF Implementation Choice:**
- From-scratch using stdlib (not scikit-learn)
- Rationale: zero dependencies, simple to audit, fast enough for target workload
- ~150 lines of pure Python

**Crash Durability (The Proof):**
```
Before 'crash': 3 runs
After 'crash': 3 runs
✓ WAL mode ensures data survives process termination
```

**Memory in Planner Prompt (The Integration Proof):**
```json
{
  "task": "show python files",
  "relevant_past_attempts": [
    {"content": "list all Python files...", "source": "runs", "status": "completed"},
    {"content": "find all .py files...", "source": "runs", "status": "completed"}
  ]
}
```

---

## Files Created/Modified

**New (518 lines):**
- `memory/__init__.py` (7)
- `memory/schema.sql` (27)
- `memory/store.py` (296)
- `memory/search.py` (153)
- `memory/importance.py` (69)

**Modified (~150 lines):**
- `agents/planner.py` - memory_results param, lesson extraction
- `core/pipeline.py` - search integration, run/lesson storage
- `interfaces/cli.py` - teach: prefix, debug commands

**Tests (726 lines):**
- `test_phase5_memory.py` - 8 comprehensive tests
- `demo_phase5_complete.py` - integration demo
- `demo_planner_prompt_proof.py` - prompt content proof
- `test_e2e_phase5.py` - end-to-end verification
- `verify_phase5.py` - component verification

---

## Core Principle Maintained

**DETERMINISTIC MEMORY, SINGLE LLM CALL**

Every memory operation is formula-based:
- **Search**: TF-IDF cosine similarity (pure math, no model)
- **Tiering**: time-based formula (no judgment)
- **Retrieval**: deterministic top-k ranking

The Planner remains the **ONLY** LLM call in Friday's entire pipeline. Lesson extraction doesn't add a second call - it piggybacks on the existing one by including optional LESSON: guidance in the system prompt.

---

## Usage

**Memory is automatic:**
- Every task execution is stored (success or failure)
- Memory search happens before planning
- Planner may emit LESSON: lines for non-obvious constraints

**Teach explicitly:**
```
> teach: always run tests before committing
Got it, I'll remember: "always run tests before committing"
```

**Check memory:**
```
> memory:stats
Total runs: 5
Total notes: 3
  taught: 2
  lesson: 1
```

---

## Phase 5 Complete

✅ SQLite WAL storage (crash-durable)  
✅ Deterministic TF-IDF search (no LLM)  
✅ Formula-based importance tiering  
✅ Explicit teaching (teach: prefix)  
✅ Planner integration (retrieval + lesson extraction)  
✅ Pipeline wiring (store runs, extract lessons)  
✅ CLI debug commands  
✅ All 8 tests passing with raw output  

**Phase 5 is production-ready. Friday now has persistent memory that learns from every task while maintaining deterministic, formula-based intelligence.**
