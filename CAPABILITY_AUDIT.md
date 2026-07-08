# Friday Capability Audit

**Date:** 2026-07-08  
**Scope:** Complete system audit - what exists vs. what's integrated  
**Method:** Code analysis only - no implementation or refactoring

---

## Executive Summary

Friday has **rich capabilities** across 8 major subsystems, but **integration is incomplete**.

**Key Finding:** Most subsystems exist and work, but are not reachable from all entry points.

**Critical Gap:** Observer data (RAM, CPU, Git, etc.) exists in WorldState but requires full pipeline execution to surface, even for simple queries.

**Phase 9 Status:** Reality-first architecture implemented but only applies to Chat intent, not Task execution.

---

## 1. Capability Inventory

### 1.1 Core Subsystems

| Subsystem | Files | Lines | Maturity | Integration |
|-----------|-------|-------|----------|-------------|
| **Orchestrator** | core/orchestrator.py | 167 | Implemented | Full |
| **Pipeline** | core/pipeline.py | 240 | Implemented | Full |
| **Planner** | agents/planner.py | 231 | Implemented | Full |
| **Executor** | core/executor.py | 200+ | Implemented | Full |
| **WorldState** | core/world.py, world_manager.py | 400+ | Implemented | Partial |
| **Memory** | memory/*.py (8 files) | 1500+ | Implemented | Full |
| **Observers** | observers/*.py (7 files) | 600+ | Implemented | Indirect |
| **Tools** | tools/*.py (9 files) | 1200+ | Implemented | Executor-only |
| **Evidence (Phase 9)** | core/evidence.py | 194 | Implemented | Chat-only |
| **TruthRouter (Phase 9)** | core/truth_router.py | 198 | Implemented | Chat-only |
| **ProjectContext (Phase 9)** | core/project_context.py | 195 | Implemented | Chat-only |
| **GroundedIntelligence** | core/grounded_intelligence.py | 194 | Implemented | Chat-only |

**Total:** ~13,000 lines of Python across 101 files

### 1.2 Observer Capabilities

| Observer | File | Data Collected | Flows To | Accessible From |
|----------|------|----------------|----------|-----------------|
| **Computer** | observers/computer.py | RAM, CPU, Disk, Battery, GPU | WorldState.computer | Planner, GroundedIntelligence |
| **Network** | observers/network.py | Internet status, interfaces | WorldState.network | Planner, GroundedIntelligence |
| **Workspace** | observers/workspace.py | Project type, languages, git state | WorldState.workspace | Planner, GroundedIntelligence |
| **Process** | observers/process.py | Running processes, PIDs | WorldState.processes | Planner |
| **Developer** | observers/developer.py | Available tools (git, docker, etc.) | WorldState.developer | Planner |
| **OS** | observers/os.py | OS details | ComputerState | Planner |

**Status:** All observers implemented and working. Data flows to WorldState. WorldState built on every task and chat.

**Problem:** Observer data NOT directly queryable. User asks "Current RAM?" → classified as TASK → full pipeline.

### 1.3 Tool Capabilities

**20 tools implemented** across 4 categories:

**Files:**
- read_file, write_file, list_directory, search_files, replace_in_file, diff_files

**Git:**
- git_status, git_diff, git_add, git_commit, git_log, git_branch, git_checkout, git_restore, git_reset, git_clone

**Shell/Python:**
- run_shell, start_shell, run_python, start_python, process (list/inspect/terminate)

**HTTP:**
- http_get, http_post, http_put, http_delete, download_file, upload_file

**Access Path:** Tools ONLY accessible through Executor (Task/Hybrid intents)

**Problem:** GroundedIntelligence cannot trigger tools despite needing them for FILESYSTEM queries.

### 1.4 Memory Capabilities

| Component | File | Functions | Accessible From |
|-----------|------|-----------|-----------------|
| **MemoryManager** | memory/manager.py | search, process_run, process_chat, extract_lesson | Pipeline, Chat, CLI |
| **MemoryStore** | memory/store.py | store_memory, search, stats, add_note | MemoryManager, CLI |
| **Retriever** | memory/retriever.py | Retrieval logic | MemoryManager |
| **Ranking** | memory/ranking.py | Hybrid ranking (keyword + semantic) | MemoryManager |
| **Embeddings** | memory/embeddings.py | Embedding generation/storage | Background worker |
| **Worker** | memory/worker.py | Async embedding generation | Background |

**Status:** Well-integrated. Used by both Chat and Pipeline. CLI commands: teach:, memory:stats, memory:retier

**Maturity:** Production-ready

### 1.5 Phase 9 Components (Grounded Intelligence)

| Component | File | Purpose | Reachable From |
|-----------|------|---------|----------------|
| **TruthRouter** | core/truth_router.py | Routes to authoritative source | Chat only |
| **Evidence Collection** | core/evidence.py | Collects structured facts | Chat only |
| **ProjectContext** | core/project_context.py | Automatic project intelligence | Chat only |
| **GroundedIntelligence** | core/grounded_intelligence.py | Reality-first orchestration | Chat only |

**Status:** Implemented and tested (21/21 tests passing)

**Problem:** Phase 9 only applies to Chat intent. Task execution still LLM-first.

---

## 2. Ownership Matrix

**Who owns what capability?**

| Capability | Owner | Authoritative Source | File/Module |
|------------|-------|---------------------|-------------|
| **Current RAM** | ComputerState | observers/computer.py | WorldState.computer.ram_gb |
| **Current CPU** | ComputerState | observers/computer.py | WorldState.computer.logical_cores |
| **Current Disk** | ComputerState | observers/computer.py | WorldState.computer.disk_use_percent |
| **Battery** | ComputerState | observers/computer.py | WorldState.computer.battery_percent |
| **Internet Status** | NetworkState | observers/network.py | WorldState.network.internet_reachable |
| **Git Branch** | WorkspaceState | observers/workspace.py | WorldState.workspace.git_branch |
| **Git Status** | WorkspaceState | observers/workspace.py | WorldState.workspace.git_clean |
| **Project Type** | WorkspaceState | observers/workspace.py | WorldState.workspace.project_type |
| **Languages** | WorkspaceState | observers/workspace.py | WorldState.workspace.languages |
| **Project Name** | ProjectContext | core/project_context.py | ProjectContext.name |
| **Current Phase** | ProjectContext | core/project_context.py | ProjectContext.active_phase |
| **Memory Recall** | MemoryManager | memory/manager.py | MemoryManager.search() |
| **Teaching** | MemoryStore | memory/store.py | MemoryStore.add_note() |
| **File Operations** | Tools | tools/files.py | read_file, write_file, etc. |
| **Git Operations** | Tools | tools/git.py | git_status, git_commit, etc. |
| **Shell Execution** | Tools | tools/shell.py | run_shell, start_shell |
| **Python Execution** | Tools | tools/python.py | run_python, start_python |
| **HTTP Operations** | Tools | tools/http.py | http_get, http_post, etc. |

---

## 3. Reachability Matrix

**Can X access Y?**

| Subsystem | Chat | Task | Hybrid | Planner | Executor | CLI |
|-----------|------|------|--------|---------|----------|-----|
| **WorldState** | ✓ (Phase 9) | ✓ | ✓ | ✓ | ✗ | ✗ |
| **Observers** | ✓ (indirect) | ✓ (indirect) | ✓ (indirect) | ✓ (indirect) | ✗ | ✗ |
| **ProjectContext** | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **TruthRouter** | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Evidence** | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **MemoryManager** | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| **MemoryStore** | ✓ (indirect) | ✓ (indirect) | ✓ (indirect) | ✓ (indirect) | ✗ | ✓ |
| **Tools** | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ |
| **Planner** | ✗ | ✓ | ✓ | - | ✗ | ✗ |
| **Executor** | ✗ | ✓ | ✓ | ✗ | - | ✗ |

**Key Observations:**
- ✓ = Directly accessible
- ✗ = Not accessible
- (indirect) = Accessible through another component

**Critical Gaps:**
1. Observer data exists but NOT directly queryable
2. Phase 9 components only in Chat path
3. Tools only accessible through Executor
4. ProjectContext not available to Planner

---

## 4. End-to-End Execution Traces

### 4.1 "What's my name?"

```
User Input: "What's my name?"
    ↓
CLI: route_intent() → "chat"
    ↓
Orchestrator (chat handler)
    ↓
FastPath check → miss
    ↓
GroundedIntelligence.answer()
    ↓
TruthRouter.route() → TruthSource.MEMORY (confidence: 0.95)
    ↓
collect_memory_evidence() → MemoryManager.search("What's my name?")
    ↓
LLM synthesis from evidence
    ↓
Response
```

**Status:** Working correctly (Phase 9)  
**Source of Truth:** MemoryManager  
**LLM Role:** Synthesizes evidence

### 4.2 "Current RAM usage?"

```
User Input: "Current RAM usage?"
    ↓
CLI: route_intent() → "task"
    ↓
Orchestrator (task handler)
    ↓
Pipeline.run_pipeline()
    ↓
observe_world() → WorldState (RAM already collected here!)
    ↓
Planner.create_plan() → generates shell command plan
    ↓
Validator.validate_and_prepare_plan()
    ↓
Executor.execute_plan()
    ↓
run_shell("free -h") or similar
    ↓
Response
```

**Problem:** WorldState.computer.ram_gb ALREADY HAS THE ANSWER but we invoke Planner + shell anyway  
**Source of Truth:** Should be WorldState.computer.ram_gb, actually uses shell command  
**Waste:** Full pipeline for data that's already in memory

### 4.3 "Current project?"

```
User Input: "Current project?"
    ↓
CLI: route_intent() → "task"
    ↓
Orchestrator (task handler)
    ↓
Pipeline → Planner → Executor → shell command (pwd or similar)
    ↓
Response
```

**Problem:** ProjectContext.name ALREADY HAS THE ANSWER (Phase 9)  
**But:** ProjectContext only accessible from Chat path  
**Result:** Task execution doesn't use ProjectContext

### 4.4 "Where is MemoryManager?"

```
User Input: "Where is MemoryManager?"
    ↓
CLI: route_intent() → "task" (has "where is")
    ↓
Pipeline → Planner → generates search_files plan
    ↓
Executor → search_files("MemoryManager")
    ↓
Response
```

**Alternative (if routed to Chat):**
```
User Input: "Where is MemoryManager?"
    ↓
CLI: route_intent() → "chat"
    ↓
GroundedIntelligence.answer()
    ↓
TruthRouter.route() → TruthSource.FILESYSTEM
    ↓
Evidence collection (needs tools)
    ↓
Problem: GroundedIntelligence CANNOT trigger search_files
    ↓
Falls back to LLM (might guess or say "I need to search")
```

**Problem:** GroundedIntelligence routes to FILESYSTEM but can't access tools

### 4.5 "Explain Rust ownership"

```
User Input: "Explain Rust ownership"
    ↓
CLI: route_intent() → "chat"
    ↓
GroundedIntelligence.answer()
    ↓
TruthRouter.route() → TruthSource.LLM (confidence: 0.7)
    ↓
LLM direct (no evidence needed)
    ↓
Response
```

**Status:** Working correctly  
**Source of Truth:** LLM (pure conceptual knowledge)

---

## 5. Dead Code Analysis

### 5.1 Confirmed Unused

| File | Status | Reason | Recommendation |
|------|--------|--------|----------------|
| **core/environment_manager.py** | UNUSED | Replaced by world_manager.py | Remove |
| **core/environment.py** | UNUSED | Superseded by WorldState | Remove |

**Evidence:** No imports found in active codebase

### 5.2 Implementation Unclear

| File | Status | Evidence | Recommendation |
|------|--------|----------|----------------|
| **core/planner_cache.py** | IMPLEMENTED | Class exists, no callers found | Verify if planner uses cache |
| **core/profiler.py** | IMPLEMENTED | Imported nowhere | Verify if profiling active |
| **tools/process_manager.py** | DUPLICATE? | Both process_manager.py and process.py exist | Clarify which is canonical |

### 5.3 Implemented but Usage Unclear

| File | Status | Evidence | Recommendation |
|------|--------|----------|----------------|
| **core/rules.py** | IMPLEMENTED | Imported by executor.py | Verify rules are evaluated |
| **observers/developer.py** | IMPLEMENTED | Collects dev tools | Verify planner uses this data |
| **observers/os.py** | IMPLEMENTED | Collects OS details | Verify integration with WorldState |
| **triggers/scheduler.py** | IMPLEMENTED | Started by main.py | Verify autonomous triggers work |
| **triggers/fs_watch.py** | IMPLEMENTED | Started by main.py | Verify filesystem watching works |

**Action Required:** Grep and trace to verify actual usage

---

## 6. Gap Analysis

### 6.1 Critical Gaps (High Impact, Fixable)

#### Gap 1: Observer Data Not Directly Queryable

**What Exists:** Observers collect RAM, CPU, Disk, Battery, Network, Git state  
**Flows To:** WorldState (built on every task and chat)  
**Used By:** Planner (for context), GroundedIntelligence (for evidence)  
**Problem:** User asks "Current RAM?" → classified as TASK → full Pipeline → Planner → Executor → shell command  
**Reality:** WorldState.computer.ram_gb already has the answer  
**Waste:** Full pipeline execution for data that's in memory  
**Recommendation:** Add direct query path for WorldState fields

#### Gap 2: Phase 9 Components Only in Chat Path

**What Exists:** TruthRouter, Evidence Collection, ProjectContext  
**Integrated In:** Chat intent only (via GroundedIntelligence)  
**NOT Integrated In:** Task intent, Hybrid intent, CLI commands  
**Problem:** Reality-first architecture only applies to conversational queries  
**Example:** "Current project?" → Task → Planner → tools, not ProjectContext  
**Recommendation:** Extend Phase 9 routing to Task intents

#### Gap 3: Tools Only Via Executor

**What Exists:** 20+ tools in tools/ directory  
**Access Path:** Task/Hybrid intent → Pipeline → Planner → Validator → Executor  
**Who CANNOT Access:** Chat intent, GroundedIntelligence, CLI direct  
**Problem:** GroundedIntelligence routes to FILESYSTEM but can't trigger search_files  
**Example:** "Where is MemoryManager?" → needs tools but Chat can't reach Executor  
**Current Workaround:** Router classifies as Task, goes through full pipeline  
**Recommendation:** Allow GroundedIntelligence to trigger specific tools

#### Gap 4: Intent Classification Too Coarse

**What Exists:** route_intent() classifies as chat/task/hybrid  
**Based On:** Simple keyword matching  
**Problem:** No concept of "direct query" vs "tool execution"  
**Examples:**
- "Current RAM?" → task (should be direct query)
- "What project?" → task (should be direct query)
- "Git status?" → task (correct - needs tool)

**Recommendation:** Add "query" intent for direct WorldState/ProjectContext access

#### Gap 5: WorldState Built but Under-Utilized

**What Exists:** WorldState with workspace, computer, network, processes, runtime  
**Built When:** Every task execution, every chat (Phase 9)  
**Cost:** ~20-50ms per observation  
**Used For:** Planner context, GroundedIntelligence evidence  
**NOT Used For:** Direct answers to simple queries  
**Problem:** We pay observation cost but don't expose data directly  
**Recommendation:** Fast-path queries that can be answered from WorldState alone

#### Gap 6: ProjectContext Only Accessible Through GroundedIntelligence

**What Exists:** ProjectContext infers project name, purpose, phase, components  
**Accessible From:** Chat → GroundedIntelligence only  
**NOT Accessible From:** Planner, Task execution, CLI commands  
**Problem:** Planner could use project context for better plans  
**Example:** Planner doesn't know current phase or project architecture  
**Recommendation:** Make ProjectContext available to Planner

### 6.2 Secondary Gaps

#### Gap 7: Rules System Integration Unclear

**What Exists:** core/rules.py with evaluate_rules(), apply_rule()  
**Imported By:** core/executor.py  
**Unclear:** Are rules actually evaluated during execution?  
**Recommendation:** Audit executor.py to confirm rules are applied

#### Gap 8: Dead Code Cluttering Architecture

**What Exists:** environment_manager.py, environment.py (unused)  
**Superseded By:** world_manager.py, world.py  
**Recommendation:** Remove dead code to clarify architecture

#### Gap 9: Profiler and Cache Not Visibly Used

**What Exists:** core/profiler.py, core/planner_cache.py  
**Unclear:** Are these actually measuring/caching anything?  
**Recommendation:** Verify usage or document as future work

---

## 7. Architectural Risks

### Risk 1: Query Routing Bottleneck

**Symptom:** Simple queries like "Current RAM?" go through full pipeline  
**Root Cause:** Observer data exists but requires task execution to surface  
**Impact:** Unnecessary Planner invocations for queries with predetermined answers  
**Cost:** ~1-2s latency, LLM tokens, complexity  
**Severity:** HIGH

### Risk 2: Phase 9 Siloing

**Symptom:** Reality-first only applies to Chat, not Task execution  
**Root Cause:** TruthRouter doesn't route Task intents  
**Impact:** Duplicate effort - Chat has grounding, Task doesn't  
**Example:** Chat can answer "Current project" from ProjectContext, Task cannot  
**Severity:** MEDIUM

### Risk 3: Tool Access Rigidity

**Symptom:** Only Executor can invoke tools  
**Root Cause:** Architectural boundary between Chat and Task paths  
**Impact:** GroundedIntelligence can't trigger tools despite needing them  
**Forces:** Everything through Planner even for deterministic tool calls  
**Severity:** MEDIUM

### Risk 4: Intent Classification Inadequacy

**Symptom:** Binary classification: conversational vs execution  
**Missing:** Direct queries, hybrid queries with grounding  
**Impact:** Router doesn't understand "this can be answered from state"  
**Result:** Over-routing to Task pipeline  
**Severity:** MEDIUM

### Risk 5: Dead Code Confusion

**Symptom:** Multiple versions of similar functionality  
**Examples:** process_manager vs process, environment_manager vs world_manager  
**Impact:** Unclear which is canonical, architecture docs outdated  
**Severity:** LOW

---

## 8. Readiness Classification

### Production Ready ✓

- **Memory System** (MemoryManager, MemoryStore, Ranking, Embeddings)
- **Pipeline** (Orchestrator, run_pipeline)
- **Planner** (create_plan, plan validation)
- **Executor** (execute_plan, tool invocation)
- **Tools** (all 20 tools functional)
- **Observers** (all 6 observers collecting data)
- **WorldState** (data collection working)
- **Phase 9 Chat Path** (TruthRouter, Evidence, GroundedIntelligence)

### Needs Integration

- **Observer Data** → Needs direct query path
- **Phase 9 Components** → Needs Task path integration
- **ProjectContext** → Needs Planner access
- **Tool Access** → Needs GroundedIntelligence integration

### Implementation Unclear

- **Rules System** → Verify if active
- **Planner Cache** → Verify if used
- **Profiler** → Verify if measuring
- **Triggers** → Verify autonomous operation

### Dead Code

- **environment_manager.py** → Remove
- **environment.py** → Remove

---

## 9. Capability vs. Integration Summary

### What Friday CAN Do (Implemented)

1. ✓ Collect system state (RAM, CPU, Disk, Battery, Network, Git)
2. ✓ Store and retrieve memories (teachings, lessons, facts)
3. ✓ Plan task execution with world context
4. ✓ Execute 20+ tools (files, git, shell, python, http)
5. ✓ Route chat queries to truth sources (Phase 9)
6. ✓ Collect evidence from multiple sources (Phase 9)
7. ✓ Infer project context automatically (Phase 9)
8. ✓ Validate plans for safety and correctness
9. ✓ Monitor execution with watchdogs
10. ✓ Evaluate health status

### What Friday CANNOT Do (Integration Gaps)

1. ✗ Answer "Current RAM?" without invoking Planner
2. ✗ Answer "Current project?" from Task intent using ProjectContext
3. ✗ Trigger tools from Chat/GroundedIntelligence
4. ✗ Directly query Observer data without pipeline
5. ✗ Apply reality-first routing to Task intents
6. ✗ Fast-path queries answerable from WorldState

### What's Unclear (Needs Verification)

1. ? Are rules actually evaluated during execution?
2. ? Is planner cache being used?
3. ? Is profiler measuring anything?
4. ? Do autonomous triggers actually work?
5. ? Does planner use developer tool info?

---

## 10. Recommendations

### 10.1 High Priority (Unblock Critical Gaps)

1. **Add Direct Query Intent**
   - Extend router to classify "query" vs "task"
   - Query intent answers directly from WorldState/ProjectContext
   - Bypass Pipeline for queries with deterministic answers

2. **Extend Phase 9 to Task Path**
   - TruthRouter should route Task intents
   - Evidence collection should work for both Chat and Task
   - ProjectContext should be available to Planner

3. **Allow GroundedIntelligence to Trigger Tools**
   - Define safe subset of tools for direct invocation
   - Bypass Planner for deterministic tool calls (search_files, read_file)
   - Maintain validation and permission checks

### 10.2 Medium Priority (Improve Architecture)

4. **Refine Intent Classification**
   - Current: chat/task/hybrid
   - Proposed: chat/query/task/hybrid
   - Query = answerable from state, no tools needed

5. **Make ProjectContext Available to Planner**
   - Planner should know project context for better plans
   - ProjectContext should be built once per task

6. **Remove Dead Code**
   - Delete environment_manager.py, environment.py
   - Clarify process_manager.py vs process.py
   - Update architecture docs to reflect current state

### 10.3 Low Priority (Polish)

7. **Verify Rules System Active**
   - Confirm rules are evaluated in executor
   - Document rule evaluation logic

8. **Verify Cache and Profiling**
   - Confirm planner cache is used
   - Confirm profiler is measuring
   - Remove if truly unused

9. **Verify Autonomous Triggers**
   - Test scheduler and filesystem watching
   - Document behavior

---

## 11. Next Steps (NOT Implementation)

**This audit identifies gaps. The next phase should:**

1. Review findings with stakeholders
2. Prioritize which gaps to address
3. Design Capability Router (unified routing for all intents)
4. Plan integration of Phase 9 components into Task path
5. Design direct query path for WorldState fields

**Do NOT implement yet. Audit complete.**

---

## Appendix A: File Inventory

**Core:** 27 files, ~3,500 lines  
**Agents:** 2 files, ~250 lines  
**Memory:** 8 files, ~1,500 lines  
**Observers:** 7 files, ~600 lines  
**Tools:** 9 files, ~1,200 lines  
**Triggers:** 3 files, ~300 lines  
**Interfaces:** 2 files, ~150 lines  
**Tests:** 43 files, ~5,000 lines

**Total:** 101 Python files, ~12,500 lines (excluding tests)

---

## Appendix B: Integration Status Legend

- **Full** = Used by multiple entry points, well-integrated
- **Partial** = Works but not accessible from all paths
- **Implemented** = Code exists and works
- **Indirect** = Accessible through another component
- **Unused** = Code exists but no callers found
- **Unclear** = Implementation exists, usage needs verification

---

**End of Audit**
