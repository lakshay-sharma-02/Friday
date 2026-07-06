# Phase 4: World Model & Continuous Observation - COMPLETE

## Summary

Phase 4 transforms Friday from a one-shot task executor into a system with continuous environmental awareness. The architecture now follows a perception loop: Observe → Plan → Execute Step → Observe → Apply Rules → Update WorldState → Continue.

## Implementation Status: ✓ COMPLETE

All requirements from the specification have been implemented and verified.

## What Was Built

### 1. WorldState - The Single Source of Truth

**File**: `core/world.py`

Replaced Phase 3's `EnvironmentState` with a typed, structured `WorldState`:

```python
@dataclass
class WorldState:
    workspace: WorkspaceState
    computer: ComputerState
    network: NetworkState
    developer: DeveloperState
    runtime: RuntimeState
    processes: ProcessState
    observed_at: datetime
```

Each component is a proper dataclass (no nested dicts):

- **WorkspaceState**: Project type, languages, build system, git state, files
- **ComputerState**: OS, CPU, RAM, disk, battery, architecture
- **NetworkState**: Internet connectivity, hostname, interfaces
- **DeveloperState**: Available tools with version info
- **RuntimeState**: Active pipeline, current step, running tool, elapsed time
- **ProcessState**: Child processes with CPU/memory tracking

### 2. RuntimeState - Friday's Self-Awareness

**File**: `core/world.py` (RuntimeState dataclass)

Tracks Friday's own execution state:
- `task_text`: Current task being executed
- `pipeline_active`: Whether pipeline is running
- `current_step`: Step number in execution
- `total_steps`: Total steps in plan
- `running_tool`: Currently executing tool
- `retry_count`: Retry attempts
- `task_start_time`: When task began
- `elapsed_seconds`: Time elapsed
- `last_observation_time`: Last observation timestamp
- `verbose_mode`: Verbose output enabled

This is live runtime state, not memory.

### 3. Process Observer

**File**: `observers/process.py`

Tracks running child processes:
- PID, command, start time
- CPU percent, memory usage (MB)
- Process status (running, finished, zombie)
- Exit code (if completed)

Uses `psutil` for objective OS-level data. No LLM involved.

### 4. Health Monitor

**File**: `core/health.py`

Objective system health evaluation:

```python
class HealthLevel(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class HealthStatus:
    level: HealthLevel
    reasons: list[str]
    cpu_percent: float
    ram_percent: float
    disk_percent: Optional[float]
    swap_percent: Optional[float]
    battery_percent: Optional[int]
    battery_charging: Optional[bool]
    internet_reachable: bool
```

Rules:
- RAM ≥95% → CRITICAL
- Disk ≥95% → CRITICAL
- Battery ≤10% (not charging) → CRITICAL
- RAM ≥85% → WARNING
- CPU ≥90% → WARNING
- Disk ≥85% → WARNING
- Battery ≤20% (not charging) → WARNING

### 5. Observation Events

**File**: `core/events.py`

Event types:
- `WORKSPACE_CHANGED`: Files modified, project changes
- `GIT_STATE_CHANGED`: Branch changes, clean/dirty state
- `PROCESS_STARTED`: New child process spawned
- `PROCESS_FINISHED`: Process completed with exit code
- `COMPUTER_HEALTH_CHANGED`: Health level transitions
- `NETWORK_CHANGED`: Internet connectivity changes
- `RUNTIME_CHANGED`: Runtime state updates

```python
@dataclass
class EventLog:
    events: list[ObservationEvent]
    max_events: int = 50
    
    def recent(count: int = 10) -> list[ObservationEvent]
    def by_type(event_type: EventType) -> list[ObservationEvent]
```

Events are synchronous, collected within the pipeline. Not async background events yet.

### 6. Deterministic Rule Engine

**File**: `core/rules.py`

OS-level rules (no AI decisions):

```python
class RuleAction(Enum):
    REDUCE_CONCURRENCY = "reduce_concurrency"
    AVOID_EXPENSIVE_WORK = "avoid_expensive_work"
    TERMINATE_PROCESS = "terminate_process"
    BLOCK_WRITES = "block_writes"
    WARN_STALL = "warn_stall"
    CONTINUE = "continue"
```

Rules implemented:
- RAM >95% → reduce concurrency
- Battery low + not charging → avoid expensive work
- Shell timeout >5min → terminate process
- Disk ≥98% → block write operations
- CPU >95% but our process idle → warn potential stall

### 7. Execution Watchdog

**File**: `core/watchdog.py`

Monitors long-running executions:

```python
@dataclass
class WatchdogState:
    tool_name: str
    started_at: float
    last_output_at: float
    last_cpu_check_at: float
    output_lines: int
    cpu_active: bool
    status: ExecutionStatus  # HEALTHY, STALLED, TIMEOUT
```

Detection:
- **Stalled**: No output for 2min + no CPU + running >3min
- **Timeout**: Running >10min (absolute maximum)

Never silently waits forever.

### 8. Continuous Observation

**File**: `core/world_manager.py`

#### Full Observation
```python
async def observe_world(
    cwd: str = ".",
    runtime: RuntimeState = None,
    tracked_pids: set[int] = None,
    refresh_only: set[str] = None,
) -> WorldState
```

Builds complete WorldState from all observers.

#### Partial Refresh Optimization

Instead of re-running all observers after every step, only refresh what could have changed:

| Tool            | Refresh Domains         |
|-----------------|-------------------------|
| `git_status`    | workspace only          |
| `shell`         | workspace + processes   |
| `write_file`    | workspace only          |
| `read_file`     | none                    |
| default         | workspace + processes   |

Example:
```python
# After git_status, only refresh workspace
refresh_domains = {"workspace"}
world = await observe_world(refresh_only=refresh_domains)
```

Near-static data (computer, developer, os) still uses 5-minute cache from Phase 3.

### 9. World Manager Architecture

Builds typed states from observer dicts:

```python
def _build_workspace_state(data: dict, cwd: str) -> WorkspaceState
def _build_computer_state(data: dict) -> ComputerState
def _build_network_state(data: dict) -> NetworkState
def _build_developer_state(data: dict) -> DeveloperState
```

Eliminates nested dicts. All components are typed dataclasses.

### 10. Planner Integration

**File**: `agents/planner.py`

Planner now receives complete context:

```python
async def create_plan(
    task: str,
    world: WorldState,
    health: HealthStatus,
    events: list[ObservationEvent],
    retry_context: str = ""
) -> list[dict]
```

System prompt updated:
```
World State context:
- Workspace: project, languages, git state, files
- Computer: OS, CPU, RAM, disk, battery, tools
- Network: connectivity, interfaces
- Processes: running children, CPU/memory
- Runtime: progress, elapsed time, retry count
- Health: system health level, resource usage
- Recent Events: what changed since last observation

Health-aware planning:
- If WARNING/CRITICAL, prefer lightweight operations
- If battery low, avoid expensive work
- If RAM/disk nearly full, avoid resource-intensive ops
- Consider recent events when planning
```

Still exactly ONE LLM call in the entire pipeline.

### 11. Continuous Observation Pipeline

**File**: `core/pipeline.py`

New architecture:

```
Observe
   ↓
Plan
   ↓
Execute Step
   ↓
Observe (partial refresh)
   ↓
Apply Rules
   ↓
Update WorldState
   ↓
Continue to next step
   ↓
Repeat
```

Key function:
```python
async def _execute_step_with_observation(
    step: dict,
    world: WorldState,
    health: HealthStatus,
    events: EventLog,
    watchdog: ExecutionWatchdog,
    tracked_pids: set[int],
) -> tuple[dict, WorldState]
```

Flow:
1. Start watchdog monitoring
2. Execute tool
3. Determine refresh domains based on tool
4. Observe with partial refresh
5. Detect changes, generate events
6. Return execution log + updated world

### 12. Verbose Output

When `VERBOSE_PIPELINE=1`:

```
[WORLD]
Workspace: python project, git clean, branch main
Computer: Linux, 12 cores, 31GB RAM
Network: internet connected
Processes: 2 active
Runtime: step 3/5, 12.4s elapsed
Health: ✓ healthy
Recent Events:
  - Git state: clean
  - Process 1234 finished with exit code 0
```

Displays after every observation cycle during development.

### 13. PipelineRun Update

**File**: `core/run.py`

Changed from Phase 3:
```python
@dataclass
class PipelineRun:
    intent: Intent
    plan: list[dict] | None = None
    execution_log: list[dict] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2
    status: str = "pending"
    world: "WorldState | None" = None  # was: environment
```

## Verification Results

All tests pass (`python test_phase4.py`):

```
✓ WorldState has all required typed components
✓ No nested dicts, all proper dataclasses
✓ Process observer returns ProcessState
✓ Health status: healthy (CPU: 49.0%, RAM: 79.1%)
✓ Event log tracks observations
✓ Rule engine triggers correctly
✓ Watchdog monitors execution
✓ World observation complete (32.4x cache speedup)
✓ Partial refresh completed in 0.006s
✓ RuntimeState tracks execution
✓ Planner receives WorldState, HealthStatus, Recent Events
```

## Architecture Changes

### Before Phase 4 (One-Shot)
```
Task → Observe Once → Plan → Execute All → Done
```

### After Phase 4 (Continuous)
```
Observe → WorldState
    ↓
Plan (with full context)
    ↓
Execute Step 1
    ↓
Observe (partial refresh) → Update WorldState
    ↓
Apply Rules
    ↓
Execute Step 2
    ↓
Observe (partial refresh) → Update WorldState
    ↓
Apply Rules
    ↓
Continue...
```

## Key Design Principles Maintained

1. **The planner remains the ONLY LLM call** ✓
2. **Every observer gathers objective facts only** ✓
3. **Every subsystem reads from WorldState** ✓
4. **WorldState is the single source of truth** ✓
5. **No memory, embeddings, or autonomous execution** ✓

## Performance Characteristics

- **Full observation**: ~1-5s (depends on subprocess checks)
- **Cached observation**: ~0.15s (32x speedup from Phase 3 cache)
- **Partial refresh (workspace only)**: ~0.006s
- **Partial refresh (workspace + processes)**: ~0.010s
- **Health evaluation**: <0.5s

## Files Created/Modified

### Created
- `core/world.py` - WorldState with typed dataclasses
- `core/health.py` - Health monitoring system
- `core/events.py` - Observation events
- `core/rules.py` - Deterministic rule engine
- `core/watchdog.py` - Execution watchdog
- `core/world_manager.py` - World observation orchestration
- `observers/process.py` - Process state observer
- `test_phase4.py` - Comprehensive tests

### Modified
- `core/pipeline.py` - Continuous observation loop
- `core/run.py` - Changed `environment` to `world`
- `agents/planner.py` - Receives WorldState + Health + Events

## What This Enables

Phase 4 establishes the architectural foundation for:

- **Memory** (Phase N): Persistent knowledge across tasks
- **Scheduler** (Phase N): Background task management
- **Background Daemon** (Phase N): Always-on Friday
- **Browser Automation** (Phase N): Web interaction observer
- **Calendar Integration** (Phase N): Time-aware planning
- **Voice** (Phase N): Audio input observer
- **Vision** (Phase N): Visual input observer
- **Robotics** (Phase N): Physical world observation

All future capabilities will plug into this world model architecture.

## Philosophy Embodied

> Friday never reasons about something it can observe, never observes something it can measure, and never measures something it can verify objectively.

Phase 4 transforms Friday from a tool executor into a system that continuously perceives its environment, understands changing context, applies deterministic rules, and makes informed decisions based on complete situational awareness.

The world changes after every action. Friday now knows this.

## Next Steps

Phase 4 is complete. Friday now operates in a continuous perception loop with:
- Typed world state (no nested dicts)
- Process tracking
- Health monitoring
- Event detection
- Rule-based safety
- Execution watchdog
- Partial refresh optimization
- Planner context enrichment

The sensory cortex is built. Friday is aware.
