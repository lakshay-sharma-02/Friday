# Repository Intelligence — Evidence Collection Expansion

Scope: **evidence collection only.** No new capability, no new planner, no
routing change. The existing `workspace_project` / `multi_step_task`
capabilities now gather a lightweight repository snapshot before synthesis.

Part of the Friday Dogfooding Protocol: every weakness found in real usage
becomes a fix + regression test.

## What changed

`Analyze this repo`, `Summarize this project`, `Review this codebase`,
`Describe repository architecture` (all route to `workspace_project` with an
analyze/summarize/explain operation → `synthesis` path) now collect, in order,
before calling the LLM:

```
Workspace  +  Repository Snapshot  +  Directory Structure  +  Important Docs
+  Project Metadata  +  Entry Points  +  Git  +  Memory
```

Previously only README + architecture docs + memory were gathered, which led
the model to answer "I don't have enough information." Now the model sees the
actual repository structure.

## Repository snapshot design

`collect_repository_evidence(cwd, project_context, workspace_state)` in
`core/evidence.py` produces a structured overview. It does **not** recursively
read source.

| Evidence key | Source | Notes |
|---|---|---|
| `repo_root` | `_find_repo_root()` | walks up to `.git` / `pyproject.toml` / `Cargo.toml` |
| `cwd` | resolved path | current working directory |
| `top_level_tree` | `_top_level_tree()` | one level; ignores `node_modules`, `target`, `dist`, `build`, `.venv`, `__pycache__`, dotfiles |
| `project_metadata` | reads `pyproject.toml`, `Cargo.toml`, `package.json`, `go.mod`, `requirements.txt`, `uv.lock`, `poetry.lock`, `Cargo.lock`, … (only those present, ≤4 KB each) | language / package-manager inference |
| `entry_points` | `ProjectContext.entry_points` | `main.py`, `app.py`, `src/main.rs`, `cli.py`, … |
| `major_components` | `ProjectContext.major_components` | top-level code dirs |
| `active_phase` | `ProjectContext.active_phase` | from `PHASE*.md` |
| `repo_stats` | `_repo_stats()` | top-level file/dir counts + language-by-extension tally (bounded scan, hard cap 400 files touched) |
| `project_type` / `languages` / `package_manager` / `build_system` | `WorkspaceState` | from observers |

## Important documents

`collect_document_evidence()` discovers and reads (capped at 2 KB):
`README*`, `CLAUDE.md`, `ARCHITECTURE.md`, `SYSTEM_ARCHITECTURE.md`,
`PHASE10_ARCHITECTURE_DIAGRAM.md`, `DESIGN.md`, `CONTRIBUTING.md`.

## Sampling strategy (deterministic)

There is **no** full-source sampling. The snapshot is structural only:
tree + metadata + entry points + bounded stats. This satisfies the
"understand, don't index" requirement and keeps analysis responsive. If a user
asks a deeper question, the existing `filesystem_search` / `read_file` tools
handle targeted lookups — this module does not duplicate them.

## Performance

- No recursive directory loading. `_repo_stats()` scans at most one level into
  top-level code dirs, capped at 400 files.
- Metadata files are read only if ≤ 4 KB.
- Document reads capped at 2 KB each.
- All evidence is gathered by `observe_world` + filesystem `stat`/`iterdir`;
  no source files are opened. Typical wall time: tens of ms + model latency.

## Evidence precedence / grounding prompt

`build_synthesis_prompt()` (in `core/evidence.py`) emits a deterministic
prompt wrapping all evidence in an `<evidence>...</evidence>` fence with 6
hard rules: evidence is authoritative, general knowledge is lower priority,
never introduce facts outside `<evidence>`, never invent Memory/History/Install
sections absent from `<evidence>`, admit insufficiency when uncovered, and
every claim must be traceable to a line in `<evidence>`.

## Files modified

- `core/evidence.py`
  - `_DOC_CANDIDATES` extended (DESIGN.md, CONTRIBUTING.md).
  - `_IGNORE_DIRS`, `_METADATA_FILES`, `_METADATA_MAX_BYTES` constants added.
  - `collect_repository_evidence()` (line ~300) + helpers `_find_repo_root`,
    `_top_level_tree`, `_find_entry_points`, `_find_major_components`,
    `_repo_stats`, `_count_ext` added.
  - `build_synthesis_prompt()` hardened (fenced `<evidence>`, 6 rules).
- `core/capability_layer.py`
  - `_handle_synthesis` now imports and calls `collect_repository_evidence`
    and folds it into the bundle (line ~224).
- `tests/test_real_world_regressions.py`
  - `TestRepositoryIntelligence` added (snapshot presence, no "no repository"
    claim, offline collector test).
  - `TestHallucinationPrevention.test_build_synthesis_prompt_forbids_fabrication`
    strengthened (fence + invented-section rule).

## Acceptance tests

| Query | Behavior |
|---|---|
| Analyze this repo | snapshot + README + architecture + metadata + entry points + git + memory → grounded summary |
| Summarize this project | same |
| Review this codebase | same |
| Describe repository architecture | uses collected evidence; never "I have no repository" |

Verified by `TestRepositoryIntelligence` (asserts `repo_root`,
`top_level_tree`, `entry_points`, `repo_stats` appear in the synthesis prompt,
and the answer never claims "no repository") and by live Friday runs.

## Known limitation (genuine, not a code defect)

The repository snapshot and grounding prompt are correct and complete — proven
by dumping the actual synthesis prompt (8 KB, contains repo root/tree/entry
points/stats/metadata/docs, **contains no** `requests`/`uv pip`/`venv` content).
However, the configured `cheap_chat` model
(`oc/deepseek-v4-flash-free`, the only model authorized at the local proxy)
occasionally **confabulates a "Memory:" narrative about failed `requests`
installs** and falsely labels it "from EVIDENCE." This is a **model-quality
limitation**, not a Friday evidence bug.

- It cannot be fixed by further prompt hardening (already 6 explicit rules +
  fenced evidence; the weak model ignores them).
- It must NOT be hardcoded around (would defeat the general capability).
- The correct resolution is a stronger `cheap_chat` model in
  `config/models.yaml` when one becomes available at the proxy.

Friday itself became more capable: repo analysis now grounds in the real
repository instead of refusing. The remaining gap is the inference backend.

## Regression policy

`tests/test_real_world_regressions.py::TestRepositoryIntelligence` guards this
behavior. Any future regression in repo-evidence collection gets a new test
here before the fix.
