# Capability Coverage Report

Generated: 2026-07-09

Scope of this sprint: **capability coverage, evidence selection, and evidence
priority only.** No new architecture, no new subsystems. Existing capability
layer (`core/capability_*`) was extended in place.

## Capabilities

Each capability declares trigger phrases (keywords/synonyms), supported
operations (from `core/operations.py`), and an evidence source (the
authoritative owner).

### System State (`system_state`)

| Capability | Triggers | Ops | Evidence source |
|---|---|---|---|
| `system_ram` | ram, ram usage, available memory, memory usage, mem | read, inspect | `WorldState.computer.ram_gb` |
| `system_cpu` | cpu, processor, cores, cpu cores | read, inspect | `WorldState.computer.logical_cores` |
| `system_disk` | disk, storage, disk space, hard drive | read, inspect | `WorldState.computer.disk_use_percent` |
| `system_battery` | battery, power, battery level | read, inspect | `WorldState.computer.battery_percent` |
| `system_network` | network, internet, connectivity, online, wifi | read, inspect | `WorldState.network.internet_reachable` |

### Workspace (`workspace`)

| Capability | Triggers | Ops | Evidence source |
|---|---|---|---|
| `workspace_project` | project, this repo, this code, repo, repository, codebase, workspace, working tree, source tree, current directory, describe this project, analyze/summarize/review this repo|codebase|project | read, summarize | `ProjectContext.name`, documents |
| `workspace_phase` | phase, milestone, current phase | read | `ProjectContext.active_phase` |
| `workspace_languages` | languages, programming languages | read | `WorldState.workspace.languages` |
| `workspace_type` | project type, type of project | read | `WorldState.workspace.project_type` |

### Git (`git`)

| Capability | Triggers | Ops | Evidence source |
|---|---|---|---|
| `git_branch` | branch, current branch | read, inspect | `WorldState.workspace.git_branch` |
| `git_status` | git status, git clean/dirty, uncommitted, repo status, working tree | read, inspect | `WorldState.workspace` |
| `git_operations` | git commit/diff/log/add, commit, diff, log | execute, modify, inspect, compare | git tools |

### Memory (`memory`)

| Capability | Triggers | Ops | Evidence source |
|---|---|---|---|
| `memory_recall` | remember, taught, teach, preference, what do i prefer, what did i teach you, what do i usually use, what have i told you, remembered preferences, do you recall | recall, remember, reflect, advise | `MemoryManager.search()` |

### Filesystem (`filesystem`)

| Capability | Triggers | Ops | Evidence source |
|---|---|---|---|
| `filesystem_search` | where is, find, search, locate, which file, implemented, search for | search, lookup | `search_files` tool |
| `filesystem_read` | read, show, cat, view file, read file | read, inspect | `read_file` tool |
| `filesystem_write` | write, create, modify, edit, update file | execute, modify | `write_file` / `replace_in_file` |

### Knowledge (`knowledge`)

| Capability | Triggers | Ops | Evidence source |
|---|---|---|---|
| `conceptual_knowledge` | explain, what is, how does, why, concept | explain, analyze, compare, advise | LLM |

### Execution (`execution`)

| Capability | Triggers | Ops | Evidence source |
|---|---|---|---|
| `multi_step_task` | install, setup, configure, build, deploy, changed, analyze/summarize/review this repo|codebase|project, how should i install, what command installs, show install command, without executing, don't execute, explain how to | execute, modify, plan, review, summarize, analyze, advise, explain | Pipeline + Planner + Executor |

## Evidence Sources

The synthesis path (`core.capability_layer._handle_synthesis`) collects, in
order, before calling the LLM:

1. **Workspace** — `ProjectContext` + `WorkspaceState` (project, languages,
   type, package manager, build system).
2. **Git** — branch, clean/dirty, modified-file count.
3. **System (observers)** — RAM, CPU cores, disk, battery, OS, internet.
4. **Documents** — `README.md`, `CLAUDE.md`, architecture docs on disk
   (`collect_document_evidence`, new).
5. **Memory** — `MemoryManager.search(query)`.

The LLM synthesis prompt now states retrieved evidence is **authoritative** and
must not be contradicted; if evidence is insufficient the model is told to say
so rather than guess (Parts 3/5).

## Evidence Priority (Part 4)

Deterministic precedence enforced in the advisor (`_handle_advise`) and the
synthesis prompt:

```
Explicit Teaching  >  Preference  >  Workspace Convention  >  General Knowledge  >  LLM Prior
```

Concretely: if memory says "use uv", the model is instructed never to suggest
pip unless the user explicitly asks to ignore their preferences. Verified by
`TestMemoryRecall.test_package_advice_respects_uv_preference`.

## Routing Vocabulary Added This Sprint (Part 2)

- **Repository:** `repo`, `repository`, `project`, `workspace`, `codebase`,
  `this repo`, `this project`, `this code`, `current code`, `current
  workspace`, `working tree`, `source tree`, `analyze this repo`,
  `analyze this codebase`, `review this project`, `summarize project`.
- **Memory recall:** `what do i prefer`, `what did i teach you`, `what do you
  remember`, `what do i usually use`, `what have i told you`,
  `remembered preferences`.
- **Package advice:** `how should i install`, `what command installs`, `how do
  i add`, `how would you install`, `show install command`, `without
  executing`, `do not install`, `don't execute`.
- **Filesystem:** `where is`, `find`, `locate`, `search for`, `which file`.

## LLM Fallback Reduction (Part 7)

Before this sprint, "analyze this repo", "summarize project", and
"describe this project" matched no capability keyword and fell through to the
"conceptual_knowledge" LLM fallback. They now route to `workspace_project` /
`multi_step_task` and collect real evidence. The LLM fallback remains only for
genuinely open-ended knowledge, creative writing, and unknown domains.

## Benchmark Results (Part 6)

| Query | Capability | Ops | Path | Pass |
|---|---|---|---|---|
| Analyze this repo | multi_step_task | analyze | synthesis | ✅ |
| Analyze this codebase | multi_step_task | analyze | synthesis | ✅ |
| Review repository | multi_step_task | review | synthesis | ✅ |
| Summarize project | workspace_project | summarize | synthesis | ✅ |
| What do I prefer? | memory_recall | read | direct | ✅ |
| What did I teach you? | memory_recall | recall | direct | ✅ |
| How should I install requests? | multi_step_task | advise | advise (no exec) | ✅ |
| Show install command for requests | multi_step_task | advise | advise (no exec) | ✅ |
| Install requests | multi_step_task | execute | pipeline | ✅ |
| Explain how to install requests | multi_step_task/conceptual | advise | advise (no exec) | ✅ |
| Create timer tool | filesystem_write | execute | pipeline | ✅ |
| Where is MemoryManager implemented? | filesystem_search | lookup | tool_direct | ✅ |
| Read README | filesystem_read | read | tool_direct | ✅ |
| Summarize README | filesystem_read | summarize | synthesis | ✅ |
| Current project? | workspace_project | read | direct | ✅ |
| Current language? | workspace_languages | read | direct | ✅ |
| Current phase? | workspace_phase | read | direct | ✅ |
| Current RAM | system_ram | read | direct | ✅ |
| CPU Usage | system_cpu | read | direct | ✅ |
| Disk | system_disk | read | direct | ✅ |
| Current Directory | workspace_project | read | direct | ✅ |
| Describe this project | workspace_project | explain | synthesis | ✅ |

## Regression Tests

`tests/test_real_world_regressions.py` (32 tests) exercises the full runtime
path with only the external LLM, memory store, and pipeline executor mocked.
Sections: `TestRepositoryAwareness`, `TestMemoryRecall`, `TestPlannerInvocation`,
`TestFilesystem`, `TestWorkspaceAndWorld`, `TestHallucinationPrevention`,
`TestTraceValidation`.

## Missing Coverage / Gaps

- **`filesystem_search` / `filesystem_read` execution:** `tool_direct` currently
  delegates back to the full pipeline (`_handle_tool_direct`); direct tool
  dispatch for safe read-only tools is not yet wired. Tests assert routing, not
  tool results.
- **LLM-fallback frequency metric:** not yet emitted. `metadata` records
  `execution_path`; a corpus-based fallback-rate counter is still TODO.
- **Memory preference precedence for execute paths:** precedence is enforced in
  the `advise`/`synthesis` prompts; the `execute`/planner path does not yet pass
  retrieved preferences into the planner prompt.

## Regression Policy (Part 12)

Every future bug found in daily use becomes one regression test in
`tests/test_real_world_regressions.py` **before** the fix lands. This suite is
the long-term quality measure, not the phase count.
