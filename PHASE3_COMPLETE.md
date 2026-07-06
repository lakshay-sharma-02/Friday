# Phase 3: Environment Awareness - COMPLETE

## Summary

Phase 3 adds a read-only observation layer that feeds structured environment data into the Planner (the single LLM call in Friday's pipeline). This enables the Planner to make informed decisions based on actual system state rather than guessing.

## Implementation Status: ✓ COMPLETE

All requirements from the specification have been implemented and verified.

## What Was Built

### 1. Core Data Structure
- **File**: `core/environment.py`
- **EnvironmentState** dataclass with fields:
  - `cwd: str`
  - `workspace: dict`
  - `computer: dict`
  - `network: dict`
  - `developer: dict`
  - `operating_system: dict`
  - `observed_at: datetime` (for cache TTL tracking)

### 2. Five Independent Observers

All observers return plain structured dicts (no formatted strings, no LLM calls):

#### workspace.py
- Project type detection (Python/Rust/Go/Java/Node)
- Languages (by presence of Cargo.toml, package.json, pyproject.toml, etc.)
- Build system (cargo, npm, maven, cmake, make)
- Test runner (pytest, cargo, go test)
- Package manager (pip, npm, cargo, maven)
- Git state: repo presence, branch, cleanliness, modified files
- Top-level files listing
- **Re-runs every task** (workspace state changes frequently)

#### network.py
- Internet reachability with **2-second hard timeout** (prevents hanging on flaky networks)
- Hostname, local IP
- Loopback availability
- DNS availability
- Network interfaces (via `ip addr show`)
- **Re-runs every task** (connectivity can change)

#### computer.py
- OS, architecture, hostname
- CPU model, logical cores
- RAM (in GB)
- Disk usage (total, used, available, percentage)
- GPU (via nvidia-smi, best effort)
- Battery status (via upower, best effort)
- Python version, current user
- **Cached for 5 minutes** (near-static data)

#### developer.py
- Tool availability and versions for: git, python, pip, uv, poetry, node, npm, pnpm, yarn, bun, cargo, rustc, go, gcc, clang, cmake, docker, kubectl, java
- Each tool checked independently (failure of one doesn't blank the rest)
- **Cached for 5 minutes** (near-static data)

#### os.py
- Platform, version, shell
- PATH summary (first 20 entries)
- Home directory, current working directory, temp directory
- Environment variables (useful subset only)
- **SECRET REDACTION**: Filters 9 keywords (key, token, secret, password, passwd, credential, auth, apikey, access) - replaces values with "[REDACTED]" while keeping keys visible
- **Cached for 5 minutes** (near-static data)

### 3. Environment Manager with Caching
- **File**: `core/environment_manager.py`
- Orchestrates all observers via `asyncio.gather()` for parallelization
- Implements 5-minute TTL cache for near-static data (computer, developer, os)
- Fresh data every call for dynamic observers (workspace, network)
- Module-level cache dict with `{"data": dict, "cached_at": datetime}` structure

### 4. Planner Integration
- **File**: `agents/planner.py`
- Planner signature: `async def create_plan(task: str, environment: EnvironmentState, retry_context: str)`
- Environment serialized to JSON via `dataclasses.asdict()`
- Included in prompt under "Environment:" section
- System prompt updated to instruct planner to use environment facts
- **Still exactly ONE LLM call** in the entire pipeline

### 5. Pipeline Integration
- **File**: `core/pipeline.py`
- Environment computed once at start: `run.environment = await inspect_environment()`
- Stored on `PipelineRun` dataclass
- Reused on retry (no re-inspection within same task run)
- Verbose output formatting via `_format_environment_verbose()` (gated by `VERBOSE_PIPELINE=1`)

### 6. Verbose Output
Example output when `VERBOSE_PIPELINE=1`:
```
[ENVIRONMENT]
Workspace: python project, git dirty, branch main
Computer: Linux, 12 cores, 31GB RAM
Network: internet connected
Developer: git ✓ python ✓ docker ✓ cargo ✓ kubectl ✗
           poetry ✗ pnpm ✗ yarn ✗ bun ✗ go ✗
```

## Verification Results

### Test 1: Project Type Detection
- ✓ Python project (Friday): detected as `python` with pyproject.toml
- ✓ Rust project: detected as `rust` with Cargo.toml, cargo build system
- ✓ Plain directory: detected as `no project` with no languages

### Test 2: Secret Redaction
- ✓ `ANTHROPIC_API_KEY` → `[REDACTED]`
- ✓ `MY_SECRET_TOKEN` → `[REDACTED]`
- ✓ `DATABASE_PASSWORD` → `[REDACTED]`
- ✓ `USER` → visible
- ✓ `PATH` → visible
- ✓ Test suite passes: `python test_secret_redaction.py`

### Test 3: Cache Performance
- First call: ~1.0s (cache MISS - runs all subprocess checks)
- Second call: ~0.03s (cache HIT - reuses cached data)
- **Speedup: 11.9x to 31.6x** depending on system load
- Cache correctly expires after 5 minutes

### Test 4: Planner Integration
- ✓ Environment JSON present in planner prompt
- ✓ All observer data (workspace, computer, network, developer, os) included
- ✓ Planner can reference specific system facts (tools available, OS, git state)

### Test 5: Pipeline Integration
- ✓ `PipelineRun` has `environment` field
- ✓ Environment computed once per task
- ✓ Environment reused on retry (no re-inspection)
- ✓ Phase 2 execution unchanged

## Core Rules Maintained

✓ **Still only ONE LLM call** in the entire pipeline (the Planner)
✓ **Every observer returns plain dict** (no formatted strings, formatting is CLI-only)
✓ **Every observer is independent** (no observer calls another observer)
✓ **Objective information only** (subprocess calls, stdlib system inspection, no guessing)
✓ **No memory, embeddings, vector databases, or autonomous execution**
✓ **Strictly read-only observation layer**
✓ **No additional model calls** anywhere in the system

## Phase 2 Execution Unchanged

- No modifications to `bus.py`, `intent.py`, `cli.py` core loop
- Tool execution logic (`core/executor.py`) untouched
- Permission tier system (`core/permissions.py`) unchanged
- This phase only adds INPUT to the planner, not execution changes

## Files Created/Modified

### Created
- `core/environment.py` - EnvironmentState dataclass
- `core/environment_manager.py` - orchestration + caching
- `observers/workspace.py` - project detection
- `observers/network.py` - connectivity checks
- `observers/computer.py` - system info
- `observers/developer.py` - tool availability
- `observers/os.py` - platform + secret redaction
- `test_secret_redaction.py` - redaction unit tests
- `test_phase3_complete.py` - comprehensive verification
- `demo_phase3.py` - verbose output demo

### Modified
- `core/pipeline.py` - added verbose formatting, environment inspection
- `core/run.py` - already had `environment` field
- `agents/planner.py` - already updated to receive environment

## Performance Characteristics

- **First environment inspection**: ~1.0s (runs ~20 subprocess version checks)
- **Cached inspection**: ~0.03s (reuses cached computer/developer/os data)
- **Cache TTL**: 5 minutes for near-static data
- **Network timeout**: 2 seconds hard limit (prevents hanging on flaky networks)

## Testing

Run comprehensive verification:
```bash
python test_phase3_complete.py
```

Run secret redaction tests:
```bash
python test_secret_redaction.py
```

Demo verbose output:
```bash
VERBOSE_PIPELINE=1 python demo_phase3.py
```

## Next Steps

Phase 3 is complete. The environment awareness layer is now feeding structured system context into the Planner, enabling it to make informed decisions about tool usage, command construction, and approach selection based on actual system state.
