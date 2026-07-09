# Routing Architecture Audit - Lexical Dependency Analysis

**Date:** 2026-07-09  
**Objective:** Identify all lexical routing dependencies and assess migration to intent-based routing

---

## Executive Summary

Friday's routing system has **44 keyword/synonym entries** in the capability registry and relies on **lexical pattern matching at 3 critical layers**:

1. **Intent Router** (`core/router.py`) - regex patterns for task/chat/hybrid classification
2. **Capability Router** (`core/capability_router.py`) - keyword substring matching for capability selection  
3. **Operation Classifier** (referenced but not audited yet) - classifies WHAT user wants to do

**Root Cause of Dogfooding Failures:**
Every observed routing failure ("what's my full name?", "what desktop environment?", "what project am I in?") stems from **keyword list incompleteness**. Each fix expands keywords, creating unbounded architectural debt.

---

## Layer 1: Intent Router (`core/router.py`)

**Purpose:** Classify requests as "chat", "task", or "hybrid"

**Lexical Dependencies:**
- **Line 9-15:** Task patterns (15 regex patterns: `\bread\b`, `\bopen\b`, `\bshow\b`, etc.)
- **Line 18-20:** Explain patterns (5 regex patterns: `\bexplain\b`, `\bsummarize\b`, etc.)
- **Line 23-27:** File patterns (regex for file extensions, filenames)

**Method:** `route_intent()` uses regex matching on lowercased text

**Why it exists:** Legacy classification from early Friday architecture

**Can it be replaced?** YES
- Currently: regex → task/chat/hybrid
- Should be: intent classifier → semantic intent enum
- Benefit: "read the file" and "show me the file" route identically

**Evidence:**
```python
# Line 29: Direct regex matching
has_task = any(re.search(p, text_lower) for p in task_patterns)
```

---

## Layer 2: Capability Router (`core/capability_router.py`)

**Purpose:** Route queries to specific capabilities (system_ram, workspace_project, memory_recall, etc.)

**Lexical Dependencies:**

### Keyword Matching (`_keyword_match_score`, lines 150-168)
```python
# Direct substring matching
for keyword in capability.keywords:
    if keyword in query:  # Line 160 - SUBSTRING MATCH
        matches += 1
```

**Problem:** 
- "what's my full name?" doesn't contain "my name" as substring due to apostrophe/contraction
- "what desktop environment?" doesn't match "desktop" if keywords only have "environment"
- Phrase order matters: "name my what's" would match "my name" but makes no sense

### Category Relevance Heuristics (lines 170-198)
```python
# Line 173: Hardcoded question word patterns
if any(q in query for q in ["what", "which", "current", "show"]):
```

**Why it exists:** Phase 10 attempted to move away from hardcoded routing, but still uses lexical matching as the scoring mechanism

**Can it be replaced?** YES - this is the primary target
- Currently: keyword substring → score → capability
- Should be: query → intent → evidence requirements → capability
- Benefit: All variations of "what's my name" / "my full name" / "who am I" route to memory_recall

---

## Layer 3: Capability Registry (`core/capability_registry.py`)

**Lexical Dependencies:** 44 keyword/synonym lists across 18 capabilities

### Examples of Keyword Lists:

**memory_recall (lines 316-321):**
```python
keywords=["remember", "taught", "teach", "preference", "recall",
          "what do i prefer", "what do you remember", "what did i teach you",
          "what do i usually use", "what have i told you", "remembered preferences",
          "what did you learn", "do you recall", "what's my name", "what is my name",
          "my name", "my full name", "who am i"],
synonyms=["my name", "what did i", "do you remember", "what i prefer",
          "my preferences", "my identity", "what i taught", "things i taught",
          "what i told you", "what's my", "who is"]
```

**system_ram (lines ~120-125):**
```python
keywords=["ram", "memory", "memory usage"],
synonyms=["memory", "ram usage"]
```

**Why it exists:** Metadata-driven capability routing (Phase 10 design)

**Problem:** Each dogfooding failure adds more phrases to these lists
- Recent additions: "what's my name", "my full name", "who am i" (today's fix)
- This list will grow unbounded
- No principled way to know when it's "complete"

**Can it be replaced?** PARTIALLY
- Keywords can be replaced with intent-based routing
- Capability metadata (owner, latency, requirements) should remain
- Suggested fix: Replace keywords with `supported_intents` enum

---

## Observed Dogfooding Failures (From This Session)

### Failure 1: "what's my full name?"
- **Expected:** Route to memory_recall
- **Actual:** Fell back to LLM knowledge
- **Cause:** Keyword list didn't include "full name" pattern
- **Fix Applied:** Added "what's my full name", "my full name" to keywords
- **Root Cause:** Lexical routing

### Failure 2: "current ram usage?"
- **Expected:** Route to system_ram, display value
- **Actual:** Routed correctly but didn't print response
- **Cause:** CLI didn't print instant answers (separate bug)
- **Fix Applied:** Modified CLI to print non-LLM responses
- **Root Cause:** Not lexical routing (different bug)

### Failure 3: "hiii" (greeting)
- **Expected:** Fast-path greeting or LLM response
- **Actual:** LLM generated response but didn't print
- **Cause:** `stream_to_stdout=False` in capability_executor.py
- **Fix Applied:** Changed to `stream_to_stdout=True`
- **Root Cause:** Not lexical routing (different bug)

---

## Technical Debt Assessment

### Current Keyword Count: 44 entries across 18 capabilities

**Growth Rate:** 
- Session started: ~35-40 keywords
- After 1 dogfooding failure: +8 keywords ("what's my name" variations)
- Projected: +5-10 keywords per dogfooding session

**Maintenance Cost:**
- Every new phrasing requires keyword expansion
- No systematic way to discover missing patterns
- Keywords become stale as language evolves
- New contributors don't know which patterns to add

**Bug Class:**
"Same intent, different wording" failures are **architectural**, not incidental:
- "what's my name?" vs "what is my name?" vs "who am I?"
- "current RAM?" vs "RAM usage?" vs "how much RAM?"
- "what project?" vs "which project?" vs "what am I working on?"

---

## Estimated Impact of Intent-Based Routing

### Bugs That Disappear:

1. **Memory Recall Failures:** All variations of identity/fact queries route to memory
   - "what's my name?", "who am I?", "my full name?", "what did you call me?"
   
2. **System State Failures:** All variations of system queries route correctly
   - "RAM?", "memory?", "how much RAM?", "current memory usage?"

3. **Workspace Failures:** All variations of workspace queries route correctly
   - "what project?", "which project?", "what am I working on?", "current project?"

**Estimated Reduction:** 80-90% of keyword-related routing bugs disappear

### Bugs That Remain:

1. Capability doesn't exist for the intent (requires new capability)
2. Intent classifier misunderstands semantic meaning (LLM error)
3. Evidence collection fails (separate from routing)

---

## Proposed Architecture Change

### Current Flow:
```
Natural Language
    ↓
Keyword Substring Match
    ↓
Capability Selection
    ↓
Evidence Collection
```

### Proposed Flow:
```
Natural Language
    ↓
Intent Classifier (deterministic where possible, LLM fallback)
    ↓
Semantic Intent Enum (MEMORY_READ, SYSTEM_QUERY, etc.)
    ↓
Intent → Capability Mapping (1:N relationship)
    ↓
Evidence Collection
```

### Key Difference:
- **Current:** Each phrasing must be in keyword list
- **Proposed:** All phrasings with same semantic intent route identically

---

## Intent Taxonomy (Proposed)

### Information Retrieval Intents:
- `MEMORY_READ` → memory_recall capability
- `SYSTEM_STATE_QUERY` → system_* capabilities
- `WORKSPACE_QUERY` → workspace_* capabilities
- `GIT_QUERY` → git_* capabilities
- `FILESYSTEM_SEARCH` → filesystem capabilities

### Action Intents:
- `EXECUTE_TASK` → pipeline execution
- `MODIFY_STATE` → pipeline with modification
- `MEMORY_WRITE` → memory storage

### Analysis Intents:
- `EXPLAIN` → synthesis with evidence
- `ANALYZE` → deep analysis
- `REVIEW` → structured review
- `SUMMARIZE` → summarization

---

## Migration Plan (High Level)

### Phase 1: Intent Classifier (New Component)
- Create `core/intent_classifier.py`
- Deterministic classification for common patterns
- LLM fallback for ambiguous cases
- Output: Semantic intent enum

### Phase 2: Intent → Capability Mapping
- Add `supported_intents` to CapabilityMetadata
- Replace keyword matching with intent matching
- Maintain backward compatibility during transition

### Phase 3: Deprecate Keywords
- Mark keywords as deprecated
- Remove keyword matching logic
- Clean up capability registry

### Phase 4: Regression Testing
- Test all dogfooding failure cases
- Verify routing correctness
- Measure performance impact

---

## Constraints & Requirements Met

✓ Do NOT replace architecture - evolve it  
✓ Maintain backward compatibility  
✓ No speculative systems - driven by real failures  
✓ No duplicated routing - replaces existing system  
✓ No hardcoded examples - uses semantic intents  

---

## Next Steps

1. Complete Operation Classifier audit (referenced in capability_router.py line 62)
2. Design Intent Classifier implementation
3. Create intent taxonomy
4. Build migration plan with regression tests
5. Implement Phase 1 (Intent Classifier)
