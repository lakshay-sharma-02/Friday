# Friday Capability Audit - Executive Summary

**Date:** 2026-07-08  
**Audit Type:** Architecture analysis only - no implementation  
**Deliverable:** CAPABILITY_AUDIT.md (615 lines, 23KB)

---

## Critical Finding

**Friday has rich capabilities but incomplete integration.**

The system contains ~13,000 lines of working code across 8 major subsystems, but many capabilities are **not reachable from all entry points**.

---

## The Core Problem

### Example: "Current RAM?"

**What Should Happen:**
```
User → WorldState.computer.ram_gb → Answer (instant)
```

**What Actually Happens:**
```
User → Task → Pipeline → Planner → Executor → shell command → Answer (2s)
```

**Why:** Observer data exists in WorldState but requires full pipeline to surface.

---

## Top 6 Gaps

1. **Observer Data Isolation** - RAM, CPU, Git data exists but not directly queryable
2. **Phase 9 Siloing** - Reality-first only in Chat, not Task execution
3. **Tool Access Rigidity** - Only Executor can invoke tools, Chat cannot
4. **Intent Classification** - No "query" intent for direct state access
5. **WorldState Under-utilized** - Built every time but not exposed directly
6. **ProjectContext Isolated** - Only Chat can access it, Planner cannot

---

## What Friday CAN Do (Implemented ✓)

- Collect system state (RAM, CPU, Disk, Battery, Network, Git)
- Store and retrieve memories (teachings, lessons, facts)
- Plan task execution with world context
- Execute 20+ tools (files, git, shell, python, http)
- Route chat queries to truth sources (Phase 9)
- Collect evidence from multiple sources (Phase 9)
- Infer project context automatically (Phase 9)

## What Friday CANNOT Do (Integration Gaps ✗)

- Answer "Current RAM?" without full pipeline
- Answer "Current project?" from Task using ProjectContext
- Trigger tools from Chat/GroundedIntelligence
- Directly query Observer data
- Apply reality-first routing to Task intents
- Fast-path queries answerable from WorldState

---

## Recommendations (Priority Order)

### High Priority

1. **Add Direct Query Intent** - Bypass pipeline for state-based queries
2. **Extend Phase 9 to Task Path** - Reality-first for all intents, not just Chat
3. **Allow Tool Access from Chat** - GroundedIntelligence needs search_files, read_file
4. **Refine Intent Classification** - Add "query" category (chat/query/task/hybrid)
5. **Remove Dead Code** - Delete environment_manager.py, environment.py

### Medium Priority

6. **Make ProjectContext available to Planner** - Better context for planning
7. **Verify Rules System** - Confirm rules are evaluated in executor
8. **Verify Cache/Profiling** - Confirm usage or remove if unused

---

## Architectural Risks

1. **Query Routing Bottleneck** - Simple queries go through full pipeline
2. **Phase 9 Siloing** - Reality-first incomplete across system
3. **Tool Access Rigidity** - Chat path cannot trigger tools
4. **Intent Classification Inadequacy** - No query vs task distinction
5. **Dead Code Confusion** - Multiple versions of similar functionality

---

## Next Steps (Design Phase, Not Implementation)

This audit identifies **what exists vs. what's integrated**.

The next phase should:

1. Review findings with stakeholders
2. Prioritize which gaps to address first
3. Design **Capability Router** (unified routing for all intents)
4. Plan Phase 9 integration into Task path
5. Design direct query path for WorldState fields

**Do NOT implement yet. Audit complete.**

---

## Audit Methodology

- Analyzed 101 Python files (~13,000 lines)
- Traced 5 representative query execution paths
- Mapped capability ownership across 8 subsystems
- Built reachability matrix (what can access what)
- Identified dead code and unclear integrations
- Verified Phase 9 implementation status

**No code modified. Analysis only.**
