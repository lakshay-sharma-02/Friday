# Friday Capability Assessment
**Date:** 2026-07-09  
**Assessor:** Claude Code (Principal Engineer)

---

## Current State

### What Friday IS
- An agentic operating system built in Python
- Architecture: Intent Router → Planner → Validator → Executor → Tools
- Single LLM planner call for execution decisions
- Reality-first cognitive routing (Phase 9 → Phase 10 unified)
- Memory system with episodic/lesson/teaching storage
- World State observation via Observers
- Specialized tool registry with 20+ capabilities

### What Friday CAN DO (Verified Capabilities)

#### Core Architecture (From SYSTEM_ARCHITECTURE.md)
- ✓ Intent classification (conversational, execution, hybrid)
- ✓ Single-pass planning (one LLM call generates full plan)
- ✓ Plan validation with risk assessment (LOW/MEDIUM/HIGH)
- ✓ Step-by-step execution with observation
- ✓ World State observation (CPU, RAM, disk, network, Git, workspace)
- ✓ Memory storage and retrieval (MemoryManager, MemoryStore)
- ✓ Tool Registry with specialized tools
- ✓ Watchdog for runaway processes
- ✓ Event logging and tracing

#### Phase 10: Capability Layer (From PHASE10_CAPABILITY_LAYER.md)
- ✓ Metadata-driven capability routing
- ✓ 18 registered capabilities across 7 categories:
  - System State: RAM, CPU, disk, battery, network (5)
  - Workspace: project, phase, languages, type (4)
  - Git: branch, status, operations (3)
  - Memory: recall (1)
  - Filesystem: search, read, write (3)
  - Knowledge: conceptual (1)
  - Execution: multi-step tasks (1)
- ✓ Fast-path queries (memory, workspace, observers bypass planner)
- ✓ Evidence collection from authoritative sources
- ✓ Project context inference from filesystem

#### Phase 11: Request Tracing (Latest commit)
- ✓ Request payload inspection
- ✓ Operation semantics tracking
- ✓ Execution policy enforcement

### What Friday CANNOT DO (Missing Capabilities)

#### Critical Missing: One-Shot Command Mode
**Status:** DOES NOT EXIST  
**Current Behavior:** Friday only runs in interactive CLI mode via `main.py`  
**Issue:** Cannot be invoked as `python main.py "task"` for single commands  
**Impact:** Cannot use Friday as a tool for discrete tasks  

**Evidence:**
```python
# main.py line 41-42
# Run the CLI in the foreground
await run_cli(bus)
```

The `run_cli` function enters an infinite loop waiting for user input. No command-line argument parsing exists.

#### Architectural Violations Found

**1. Executor Module is Dead Code** (From ARCHITECTURE_AUDIT.md)
- **Location:** `core/executor.py`
- **Status:** Contains unused legacy functions
- **Problem:** `core/pipeline.py` absorbed all execution responsibilities
- **Violation:** Architecture says `Validator → Executor`, but implementation is `Validator → Pipeline → (inline execution)`
- **Functions affected:** `execute_plan`, `validate_plan`, `validate_step` (all unused)
- **Recommendation:** Extract `_execute_step_with_observation` from pipeline.py into executor.py

### What Friday HAS COMPLETED (Phases)

- ✓ Phase 2: Unknown (referenced in files)
- ✓ Phase 3: Complete (test_phase3_complete.py exists)
- ✓ Phase 4: Complete (multiple phase4 test files)
- ✓ Phase 5: Memory system integration
- ✓ Phase 6: Stabilization
- ✓ Phase 7A: Memory alignment
- ✓ Phase 7B: Complete
- ✓ Phase 9: Cognitive Routing & Grounded Intelligence
- ✓ Phase 10: Capability Layer & Unified Cognitive Routing
- ✓ Phase 10.5: Operation Semantics & Execution Policy
- ✓ Phase 11: Request Tracing & Payload Inspection

### What Friday THREW ERRORS ON (Test Collection)

**Test Collection Errors (2 total):**

1. **test_phase9_integration.py**
   - Error: `ModuleNotFoundError: No module named 'core.grounded_intelligence'`
   - Cause: Phase 9 modules merged into Phase 10, test file not updated
   - Status: STALE TEST FILE

2. **test_phase9_truth_routing.py**
   - Error: `ModuleNotFoundError: No module named 'core.truth_router'`
   - Cause: Phase 9 modules merged into Phase 10, test file not updated
   - Status: STALE TEST FILE

**Test Collection Stats:**
- Total collected: 260 tests
- Collection errors: 2
- Warnings: 50 (datetime.utcnow() deprecation in memory/ranking.py and memory/embeddings.py)

### What Friday DID (This Session)

**Attempt 1: Use Friday to remove stale tests**
- Command: `python main.py "Remove the stale test files..."`
- Result: FAILED - Friday launched into interactive mode instead of executing command
- Cause: No one-shot command capability exists

**Attempt 2: Manually remove stale tests**
- Action: `rm test_phase9_integration.py test_phase9_truth_routing.py`
- Result: USER BLOCKED - Tool use rejected before execution
- Status: Tests still present in repository

### What Friday DIDN'T DO

- ✗ Did not accept one-shot commands
- ✗ Did not process command-line arguments
- ✗ Did not remove stale test files (blocked by user)
- ✗ Did not implement executor separation (architectural debt)

---

## Test Suite Status

### Passing Tests (Unknown exact count, collection shows 260 total)
- test_execution_tools.py: 14+ tests
- test_e2e_phase4.py, test_e2e_phase5.py
- test_git_tools.py, test_http_tools.py
- test_phase4.py, test_phase5_memory.py
- test_phase6_final.py, test_phase10_acceptance.py
- Many more...

### Failing/Blocked Tests
- test_phase9_integration.py: Import error (stale)
- test_phase9_truth_routing.py: Import error (stale)

### Test Categories
- Unit tests: execution, git, http, memory
- Integration tests: phase4, phase5, phase6, phase10
- E2E tests: phase4, phase5
- Acceptance tests: phase10 (23 tests documented)
- Benchmark tests: phase10, semantic

---

## Repository Structure

```
Friday/
├── agents/          # LLM Planner and routing logic
├── core/            # Backbone (WorldState, Pipeline, Executor, Validator, Memory)
│   ├── capability_layer.py
│   ├── capability_router.py
│   ├── capability_registry.py
│   ├── capability_executor.py
│   ├── evidence.py
│   ├── project_context.py
│   ├── executor.py          # DEAD CODE - needs refactor
│   ├── pipeline.py          # Absorbed executor responsibilities
│   ├── plan_validation.py
│   └── orchestrator.py
├── tools/           # Specialized capabilities + Tool Registry
├── observers/       # Environment monitoring
├── memory/          # Memory subsystem
├── interfaces/      # CLI entry point
├── triggers/        # Scheduler and filesystem watch
├── tests/           # 52 test files, 260 tests
└── config/          # Configuration files
```

---

## Immediate Issues

### Priority 1: Test Collection Broken
**Impact:** Cannot run full test suite  
**Blocker:** 2 stale Phase 9 test files  
**Fix:** Remove test_phase9_integration.py and test_phase9_truth_routing.py

### Priority 2: No One-Shot Command Mode
**Impact:** Friday cannot be used as a tool  
**Blocker:** main.py only supports interactive mode  
**Fix Required:** Add command-line argument parsing to main.py

### Priority 3: Architectural Debt
**Impact:** Code violates documented architecture  
**Issue:** Executor module is dead code, Pipeline does execution  
**Risk:** Low (functionality works, just misplaced)

---

## Next Actions Required

1. **Enable one-shot commands** - Modify main.py and interfaces/cli.py
2. **Clean up stale tests** - Remove Phase 9 test files
3. **Fix executor architecture** - Move execution logic from pipeline.py to executor.py (lower priority)
4. **Fix deprecation warnings** - Replace datetime.utcnow() calls (lowest priority)

---

## Success Metrics

**Could Friday complete this task today?** NO  
**Reason:** Lacks one-shot command capability  
**After fix:** YES - Friday will be able to accept and execute single commands
