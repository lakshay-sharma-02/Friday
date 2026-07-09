# Architectural Comparison: Intent-Based vs Evidence-Based Routing

**Date:** 2026-07-09  
**Purpose:** Challenge the Intent Classification proposal and evaluate Evidence Planning as an alternative

---

## The Core Question

Should Friday ask:
- **Approach A:** "What does the user want to do?" (Intent) → then find evidence
- **Approach B:** "What information does the user need?" (Evidence) → then collect it

---

## Approach A: Intent-Based Routing

### Flow:
```
Natural Language
    ↓
Intent Classifier (MEMORY_READ, SYSTEM_QUERY, WORKSPACE_QUERY, etc.)
    ↓
Capability Selection (intent → capability mapping)
    ↓
Evidence Collection
    ↓
LLM Synthesis
```

### Example: "What's my full name?"
1. Classify intent: `MEMORY_READ`
2. Map to capability: `memory_recall`
3. Collect evidence: `MemoryManager.search("full name")`
4. Synthesize with LLM

### Problems:

**Problem 1: Intent taxonomy grows unbounded**
- Need: `MEMORY_READ`, `MEMORY_WRITE`, `SYSTEM_QUERY`, `WORKSPACE_QUERY`, `GIT_QUERY`, `FILESYSTEM_SEARCH`, `EXECUTE_TASK`, `MODIFY_STATE`, `EXPLAIN`, `ANALYZE`, `REVIEW`, `SUMMARIZE`, etc.
- Each new capability domain requires new intent types
- Intent becomes another keyword table (just enum instead of strings)

**Problem 2: Ambiguous queries map to multiple intents**
- "What desktop environment do I use?" could be:
  - `MEMORY_READ` (if user taught Friday their preference)
  - `SYSTEM_QUERY` (if Friday should detect it from running processes)
  - `WORKSPACE_QUERY` (if it's project-specific config)
- Intent classifier must guess which source is authoritative

**Problem 3: Intent doesn't match Friday's architecture**
- Friday's subsystems are organized by **evidence source**, not intent:
  - Memory (historical facts)
  - Workspace (project state)
  - Observers (system state)
  - Git (version control state)
  - Evidence (collected artifacts)
- Intent is orthogonal to evidence source

**Problem 4: Multi-evidence queries require multiple intents**
- "Analyze this repository" needs:
  - `WORKSPACE_QUERY` (project type, languages)
  - `GIT_QUERY` (history, contributors)
  - `FILESYSTEM_SEARCH` (structure, files)
  - `ANALYZE` (synthesis)
- Which is "the" intent? All of them?

---

## Approach B: Evidence-Based Routing

### Flow:
```
Natural Language
    ↓
Evidence Requirements (What information is needed?)
    ↓
Evidence Source Selection (Which sources have this information?)
    ↓
Evidence Collection (Parallel retrieval from all sources)
    ↓
LLM Synthesis
```

### Example: "What's my full name?"
1. Determine evidence needed: `user identity facts`
2. Find sources: Memory (teachings, preferences), possibly Workspace (git user.name)
3. Collect from all sources in parallel
4. LLM synthesizes from available evidence

### Example: "What desktop environment do I use?"
1. Determine evidence needed: `desktop environment information`
2. Find sources: Memory (preferences), System (running processes), Workspace (configs)
3. Collect from all sources in parallel
4. LLM synthesizes, preferring explicit teachings over detected state

### Example: "Analyze this repository"
1. Determine evidence needed: `repository structure, history, languages, patterns`
2. Find sources: Workspace (languages, project type), Git (history, contributors), Filesystem (structure)
3. Collect from all sources in parallel
4. LLM synthesizes comprehensive analysis

---

## Comparison Matrix

| Dimension | Approach A: Intent | Approach B: Evidence | Winner |
|-----------|-------------------|---------------------|---------|
| **Special cases** | Need intent per capability domain + hybrid intents | Evidence sources are fixed architectural components | **Evidence** |
| **Scalability** | New capabilities require new intents | New capabilities declare which evidence they provide | **Evidence** |
| **Keyword debt removal** | Replaces keywords with intent enums (still grows) | No keywords, no intents - only evidence types | **Evidence** |
| **LLM routing calls** | May need LLM to classify ambiguous intents | May need LLM to determine evidence requirements | **Tie** |
| **Architecture match** | Intent is new abstraction orthogonal to existing systems | Evidence sources ARE Friday's existing systems | **Evidence** |
| **Multi-source queries** | Requires multiple intents or hybrid classification | Natural: collect from multiple sources | **Evidence** |

---

## Deep Dive: Why Evidence Planning Eliminates More Bugs

### The Routing Bug Pattern:

Current system fails when:
- "What's my full name?" → doesn't match keywords → falls back to LLM
- "What desktop environment?" → doesn't match keywords → falls back to LLM
- "What project am I in?" → doesn't match keywords → falls back to LLM

**Intent-based solution:**
- Classify intent → map to capability → collect evidence
- Still fails if: intent classifier misunderstands phrasing
- Still requires: growing taxonomy of intents

**Evidence-based solution:**
- Determine evidence needed → collect from all relevant sources
- Fails if: evidence requirement determination is wrong
- But: Evidence types are stable (Memory, Workspace, Git, System - these don't grow)

### Key Insight: Evidence Sources Are Stable

Friday's evidence sources:
1. **Memory** - User teachings, preferences, lessons, facts
2. **Workspace** - Project metadata, languages, config
3. **Git** - Repository history, branches, commits
4. **System** - RAM, CPU, disk, battery, network
5. **Filesystem** - Files, directories, content
6. **Observers** - Running processes, environment

These are **architectural invariants**. New capabilities don't add new evidence sources - they just use existing sources differently.

Compare to intents, which grow:
- Add calendar capability → need `CALENDAR_READ`, `CALENDAR_WRITE` intents
- Add email capability → need `EMAIL_READ`, `EMAIL_SEND` intents
- Add database capability → need `DB_QUERY`, `DB_MODIFY` intents

Evidence sources don't grow this way. Calendar uses Memory + Filesystem. Email uses Memory + Filesystem. Database uses Filesystem + Memory.

---

## How Evidence Planning Works

### Phase 1: Evidence Requirement Determination

**Input:** Natural language query  
**Output:** List of evidence types needed

Examples:
- "What's my full name?" → `[UserIdentity]` → Sources: Memory
- "Current RAM usage?" → `[SystemState.RAM]` → Sources: System Observers
- "What project am I in?" → `[WorkspaceContext]` → Sources: Workspace
- "Analyze this repository" → `[WorkspaceContext, GitHistory, FileStructure]` → Sources: Workspace, Git, Filesystem

**Implementation:**
- Deterministic patterns for common evidence types
- LLM fallback for complex queries
- Returns: `List[EvidenceRequirement]`

### Phase 2: Evidence Source Selection

**Input:** Evidence requirements  
**Output:** Sources to query

```python
class EvidenceSource:
    MEMORY = "memory"
    WORKSPACE = "workspace" 
    GIT = "git"
    SYSTEM = "system"
    FILESYSTEM = "filesystem"

evidence_source_map = {
    EvidenceType.USER_IDENTITY: [EvidenceSource.MEMORY, EvidenceSource.WORKSPACE],
    EvidenceType.SYSTEM_STATE: [EvidenceSource.SYSTEM],
    EvidenceType.WORKSPACE_CONTEXT: [EvidenceSource.WORKSPACE],
    EvidenceType.GIT_HISTORY: [EvidenceSource.GIT],
    EvidenceType.FILE_STRUCTURE: [EvidenceSource.FILESYSTEM],
}
```

This mapping is **static** and **comprehensive**. No keywords. No growth.

### Phase 3: Evidence Collection

**Input:** Sources to query  
**Output:** Evidence bundle

Collect from all sources **in parallel**:
```python
evidence = {}
if EvidenceSource.MEMORY in sources:
    evidence['memory'] = await memory_manager.search(query)
if EvidenceSource.WORKSPACE in sources:
    evidence['workspace'] = await observe_workspace()
if EvidenceSource.SYSTEM in sources:
    evidence['system'] = await observe_system()
# etc.
```

### Phase 4: LLM Synthesis

**Input:** Query + Evidence bundle  
**Output:** Answer

LLM receives:
- Original query
- All collected evidence with source attribution
- Synthesis instruction

The LLM never needs to know about intents or capabilities. It just has evidence.

---

## Answering the 6 Questions

### 1. Which architecture produces fewer special cases?

**Evidence Planning: Significantly fewer**

Intent-based needs:
- Intent taxonomy (15+ intent types)
- Intent-to-capability mapping rules
- Hybrid intent handling
- Multi-intent query decomposition

Evidence-based needs:
- Evidence type enum (stable, ~10 types)
- Evidence-to-source mapping (static)

**Winner: Evidence Planning**

### 2. Which architecture scales better to hundreds of capabilities?

**Evidence Planning: Much better**

Intent-based:
- 100 capabilities → ~30-50 intent types (grows with capability domains)
- Each new domain requires new intents

Evidence-based:
- 100 capabilities → same 6 evidence sources
- New capabilities declare what evidence they provide, not what intents they serve

Example: Adding 50 new "developer tool" capabilities
- Intent-based: Add `GIT_QUERY`, `DOCKER_QUERY`, `K8S_QUERY`, `CI_QUERY`, etc.
- Evidence-based: All use existing Workspace, Filesystem, System sources

**Winner: Evidence Planning**

### 3. Which architecture removes more keyword debt?

**Evidence Planning: Removes all keywords**

Intent-based:
- Removes keyword strings
- Replaces with intent enum values
- Intent classifier still needs patterns to map queries to intents

Evidence-based:
- No keywords
- No intents
- Only evidence types (which are stable architectural components)

**Winner: Evidence Planning**

### 4. Which architecture minimizes LLM routing?

**Tie, but Evidence has an advantage**

Intent-based:
- LLM may be needed to classify ambiguous intents
- "What desktop environment?" could be MEMORY_READ or SYSTEM_QUERY

Evidence-based:
- LLM may be needed to determine evidence requirements
- But evidence determination is simpler: "What info is needed?" not "What action is intended?"

Additional advantage for Evidence:
- Can collect from multiple sources speculatively
- LLM synthesis handles conflicts naturally
- "If I taught you my DE, use that; otherwise detect it"

**Winner: Evidence Planning (slight edge)**

### 5. Which architecture best matches Friday's existing systems?

**Evidence Planning: Perfect match**

Friday's existing architecture:
```
Memory (MemoryManager, MemoryStore, MemoryRetriever)
    ↓
Workspace (observers.workspace, ProjectContext)
    ↓  
Git (tools.git, WorldState.workspace.git_*)
    ↓
System (observers.computer, observers.network)
    ↓
Evidence (core/evidence.py - Phase 10)
    ↓
Planner
    ↓
Executor
```

Evidence Planning maps 1:1 to these components.

Intent Classification is orthogonal - it's a new abstraction that cuts across existing boundaries.

**Winner: Evidence Planning (not even close)**

### 6. Would an Evidence Planner naturally eliminate most routing bugs?

**Yes. Here's why:**

Current bug: "What's my full name?" → keyword mismatch → LLM fallback (no memory access)

Evidence Planning:
1. Determine evidence: `[UserIdentity]`
2. Sources: Memory, Workspace (git user)
3. Collect both in parallel
4. LLM synthesizes from available evidence

**The bug disappears because:**
- No keyword matching
- No intent classification
- Just: "This query needs user identity facts" → collect from sources → synthesize

Same for all observed failures:
- "What desktop environment?" → Evidence: UserPreferences + SystemState → collect both
- "What project am I in?" → Evidence: WorkspaceContext → collect from Workspace observer
- "Analyze repository" → Evidence: WorkspaceContext + GitHistory + FileStructure → collect all

**Winner: Evidence Planning eliminates the entire bug class**

---

## The Critical Difference

### Intent asks: "What action does the user want?"
- This is **user-centric** thinking
- Requires modeling user goals
- Goals are unbounded

### Evidence asks: "What information is needed?"
- This is **system-centric** thinking
- Requires modeling information sources
- Sources are bounded (architectural components)

**Friday's architecture is already organized by information sources, not user goals.**

Evidence Planning aligns with the existing architecture.  
Intent Classification fights against it.

---

## Recommendation

**Reject the Intent Classification proposal.**

**Adopt Evidence Planning instead.**

### Why:

1. **Fewer special cases** - Evidence types are stable, intents grow
2. **Better scalability** - New capabilities use existing evidence sources
3. **Removes all keyword debt** - No keywords, no intents, only evidence types
4. **Matches existing architecture** - Evidence sources ARE Friday's subsystems
5. **Eliminates routing bugs** - Multi-source collection handles ambiguity naturally
6. **Simpler long-term** - 6 evidence sources vs dozens of intent types

### Implementation Path:

1. **Evidence Type Enum** - Define stable evidence types (UserIdentity, SystemState, WorkspaceContext, etc.)
2. **Evidence Requirement Planner** - Determine what evidence a query needs
3. **Evidence Source Mapping** - Static map from evidence types to sources
4. **Parallel Evidence Collection** - Query all relevant sources concurrently
5. **LLM Synthesis** - Synthesize answer from evidence bundle

### What NOT to build:

- Intent taxonomy
- Intent classifier
- Intent-to-capability mapping
- Hybrid intent handlers

---

## Proof: Evidence Planning Eliminates Keyword Debt

Current system: 44 keyword entries  
Intent-based: ~15-20 intent enum values (still grows)  
Evidence-based: **6 evidence sources (stable)**

Evidence sources are not just "fewer keywords" - they're **architectural invariants**:
- Memory exists because Friday needs to remember
- Workspace exists because Friday needs project context
- Git exists because Friday needs version control
- System exists because Friday needs host information
- Filesystem exists because Friday needs file access

These don't change. New capabilities just use these sources differently.

Intent types, by contrast, grow with capability domains:
- Calendar → CALENDAR_READ, CALENDAR_WRITE
- Email → EMAIL_READ, EMAIL_SEND  
- Database → DB_QUERY, DB_MODIFY

**Evidence Planning is the simplest architecture that eliminates the largest class of routing failures.**

---

## Architectural Verdict

The audit correctly identified lexical routing debt.

The audit's proposed solution (Intent Classification) solves the symptom but not the root cause.

**Root cause:** Friday routes by matching user phrasings to capabilities, when it should route by matching information needs to evidence sources.

**Correct solution:** Evidence Planning

**Implementation status:** Do not implement Intent Classification. Design Evidence Planning instead.
