# Friday Capability Matrix

**Phase 10: Unified Cognitive Routing**  
**Generated:** 2026-07-08

This matrix documents every capability in Friday's cognitive system, showing ownership, requirements, and execution characteristics.

---

## System State Capabilities

Instant answers from WorldState. Never use shell or LLM.

| Capability | Owner | Source | Planner | Executor | LLM | Tools | Latency | Evidence |
|------------|-------|--------|---------|----------|-----|-------|---------|----------|
| **system_ram** | observers.computer | WorldState.computer.ram_gb | ✗ | ✗ | ✗ | none | instant | ✓ |
| **system_cpu** | observers.computer | WorldState.computer.logical_cores | ✗ | ✗ | ✗ | none | instant | ✓ |
| **system_disk** | observers.computer | WorldState.computer.disk_use_percent | ✗ | ✗ | ✗ | none | instant | ✓ |
| **system_battery** | observers.computer | WorldState.computer.battery_percent | ✗ | ✗ | ✗ | none | instant | ✓ |
| **system_network** | observers.network | WorldState.network.internet_reachable | ✗ | ✗ | ✗ | none | instant | ✓ |

**Entry Points:** CapabilityExecutor._execute_system_state() → WorldState direct access  
**Never:** Shell commands, LLM synthesis, tool execution

---

## Workspace Capabilities

Project context from ProjectContext and WorkspaceState. Instant, deterministic.

| Capability | Owner | Source | Planner | Executor | LLM | Tools | Latency | Evidence |
|------------|-------|--------|---------|----------|-----|-------|---------|----------|
| **workspace_project** | core.project_context | ProjectContext.name | ✗ | ✗ | ✗ | none | instant | ✓ |
| **workspace_phase** | core.project_context | ProjectContext.active_phase | ✗ | ✗ | ✗ | none | instant | ✓ |
| **workspace_languages** | observers.workspace | WorldState.workspace.languages | ✗ | ✗ | ✗ | none | instant | ✓ |
| **workspace_type** | observers.workspace | WorldState.workspace.project_type | ✗ | ✗ | ✗ | none | instant | ✓ |

**Entry Points:** CapabilityExecutor._execute_workspace() → ProjectContext/WorkspaceState  
**Never:** LLM hallucination, file system queries

---

## Git Capabilities

Git state from WorldState (instant) or git tools (moderate latency).

| Capability | Owner | Source | Planner | Executor | LLM | Tools | Latency | Evidence |
|------------|-------|--------|---------|----------|-----|-------|---------|----------|
| **git_branch** | observers.workspace | WorldState.workspace.git_branch | ✗ | ✗ | ✗ | none | instant | ✓ |
| **git_status** | observers.workspace | WorldState.workspace.git_clean | ✗ | ✗ | ✗ | none | instant | ✓ |
| **git_operations** | tools.git | git tools | ✓ | ✓ | ✗ | git_commit, git_diff, git_log, git_add | moderate | ✓ |

**Entry Points:**  
- Read-only state: CapabilityExecutor._execute_git() → WorldState  
- Write operations: Pipeline → Planner → Executor → git tools

**Never:** git_status and git_branch should never invoke shell commands

---

## Memory Capabilities

Recall teachings, lessons, and preferences from MemoryManager.

| Capability | Owner | Source | Planner | Executor | LLM | Tools | Latency | Evidence |
|------------|-------|--------|---------|----------|-----|-------|---------|----------|
| **memory_recall** | memory.manager | MemoryManager.search() | ✗ | ✗ | ✓ | none | fast | ✓ |

**Entry Points:** CapabilityExecutor._execute_memory() → MemoryManager.search()  
**LLM Usage:** Only for synthesizing retrieved memories, not for inventing them  
**Never:** LLM should never invent memories that aren't in MemoryStore

---

## Filesystem Capabilities

File operations through specialized tools. Never LLM hallucination.

| Capability | Owner | Source | Planner | Executor | LLM | Tools | Latency | Evidence |
|------------|-------|--------|---------|----------|-----|-------|---------|----------|
| **filesystem_search** | tools.files | search_files tool | ✗ | ✓ | ✗ | search_files | moderate | ✓ |
| **filesystem_read** | tools.files | read_file tool | ✗ | ✓ | ✗ | read_file | fast | ✓ |
| **filesystem_write** | tools.files | write_file tool | ✓ | ✓ | ✗ | write_file, replace_in_file | moderate | ✓ |

**Entry Points:**  
- Search/Read: CapabilityExecutor marks needs_tools → Pipeline → Executor  
- Write: Requires full Pipeline (planning + validation + execution)

**Never:** LLM should never guess file locations or contents

---

## Knowledge Capabilities

Pure conceptual knowledge from LLM. No grounded evidence.

| Capability | Owner | Source | Planner | Executor | LLM | Tools | Latency | Evidence |
|------------|-------|--------|---------|----------|-----|-------|---------|----------|
| **conceptual_knowledge** | core.model_client | LLM | ✗ | ✗ | ✓ | none | slow | ✗ |

**Entry Points:** CapabilityExecutor._execute_knowledge() → call_model()  
**Use Cases:** Explain concepts, compare patterns, answer "what is" / "how does" / "why"  
**Never:** Used for factual queries about system state or project context

---

## Execution Capabilities

Complex multi-step tasks requiring planning and orchestration.

| Capability | Owner | Source | Planner | Executor | LLM | Tools | Latency | Evidence |
|------------|-------|--------|---------|----------|-----|-------|---------|----------|
| **multi_step_task** | core.pipeline | Pipeline + Planner + Executor | ✓ | ✓ | ✓ | various | slow | ✓ |

**Entry Points:** CapabilityLayer._handle_pipeline() → Pipeline → Planner → Validator → Executor  
**Use Cases:** Install dependencies, setup environments, build projects, complex refactorings  
**Characteristics:** Full observe → plan → validate → execute cycle

---

## Capability Ownership Rules

### 1. System State → Observers → WorldState
- **Who:** observers.computer, observers.network
- **When:** RAM, CPU, disk, battery, network status
- **How:** Direct WorldState field access
- **Never:** Shell commands, /proc reads, system calls

### 2. Workspace → ProjectContext
- **Who:** core.project_context, observers.workspace
- **When:** Project name, phase, languages, type
- **How:** ProjectContext.from_workspace() or WorldState.workspace
- **Never:** README parsing by LLM, file system guessing

### 3. Git → WorldState (state) or git tools (operations)
- **Who:** observers.workspace (state), tools.git (operations)
- **When State:** Branch, clean/dirty status
- **When Operations:** Commit, diff, log, add
- **How State:** WorldState.workspace.git_*
- **How Operations:** Through Executor with git tools
- **Never:** git_branch or git_status should invoke shell

### 4. Memory → MemoryManager
- **Who:** memory.manager
- **When:** Teachings, lessons, preferences, recall
- **How:** MemoryManager.search() for retrieval
- **Never:** LLM inventing memories

### 5. Filesystem → Executor + Tools
- **Who:** tools.files
- **When:** Find files, read files, write files
- **How:** Through Executor invoking search_files, read_file, write_file
- **Never:** LLM guessing file locations or contents

### 6. Knowledge → LLM
- **Who:** core.model_client
- **When:** Conceptual explanations, comparisons, "what is" / "why"
- **How:** Direct call_model()
- **Never:** Used for system state or project facts

### 7. Execution → Pipeline
- **Who:** core.pipeline, agents.planner, core.executor
- **When:** Multi-step tasks, installations, complex operations
- **How:** Full observe → plan → validate → execute cycle
- **Never:** Simple queries that can be answered directly

---

## Execution Paths

### Path 1: Direct (instant)
**Capabilities:** system_*, workspace_*, git_branch, git_status  
**Flow:** Query → Router → Executor → WorldState/ProjectContext → Answer  
**Latency:** <10ms  
**No:** Planner, Executor (tools), LLM

### Path 2: Tool Direct (fast to moderate)
**Capabilities:** filesystem_read, filesystem_search (future)  
**Flow:** Query → Router → Pipeline → Executor → Tool → Answer  
**Latency:** <1s  
**No:** Planner (for simple reads)

### Path 3: Pipeline (moderate to slow)
**Capabilities:** filesystem_write, git_operations, multi_step_task  
**Flow:** Query → Router → Pipeline → Planner → Validator → Executor → Tools → Answer  
**Latency:** 1s+  
**Yes:** Full pipeline with planning and validation

### Path 4: LLM (slow)
**Capabilities:** conceptual_knowledge, memory_recall (synthesis)  
**Flow:** Query → Router → Executor → LLM → Answer  
**Latency:** Variable (LLM latency)  
**When:** No grounded evidence available

---

## Multi-Capability Fusion

Some queries require multiple capabilities working together.

### Example: "Review this repository"
**Capabilities Needed:**
1. filesystem_search → Find all files
2. git_status → Check git state
3. workspace_project → Project context
4. conceptual_knowledge (LLM) → Synthesize review

**Execution:** Routes to multi_step_task → Pipeline coordinates all capabilities

### Example: "What changed since yesterday?"
**Capabilities Needed:**
1. git_operations → git log / git diff
2. memory_recall → Remember what "yesterday" means in context
3. workspace_project → Project context

**Execution:** Routes to multi_step_task or git_operations depending on complexity

---

## Anti-Patterns

### ❌ DO NOT: Bypass Ownership
```python
# WRONG: Direct shell call for RAM
result = subprocess.run(["free", "-h"])

# RIGHT: Use WorldState
ram_gb = world.computer.ram_gb
```

### ❌ DO NOT: LLM Hallucination for Facts
```python
# WRONG: Ask LLM where files are
answer = await call_model("Where is MemoryManager?")

# RIGHT: Use filesystem_search capability
decision = router.route("Where is MemoryManager?")
# Routes to filesystem_search → search_files tool
```

### ❌ DO NOT: Invoke Planner for Simple Queries
```python
# WRONG: Full pipeline for RAM query
run_pipeline(PipelineRun(Intent(payload={"text": "Current RAM?"})))

# RIGHT: Direct capability execution
result = await executor.execute(system_ram_capability, query, world)
```

### ❌ DO NOT: Duplicate Subsystem Functionality
```python
# WRONG: Reimplementing memory search
def search_memories(query):
    # custom search logic...

# RIGHT: Delegate to MemoryManager
results = memory_manager.search(query)
```

---

## Capability Keywords

Keywords and synonyms for routing. Router scores based on these.

### System State
- **RAM:** ram, ram usage, available memory, memory usage, mem
- **CPU:** cpu, processor, cores, cpu cores
- **Disk:** disk, storage, disk space, disk usage, hard drive
- **Battery:** battery, power, battery level, battery percent, battery status, power level
- **Network:** network, internet, connectivity, online, internet status, connection, wifi

### Workspace
- **Project:** project, project name, current project, what project, which project
- **Phase:** phase, milestone, current phase, what phase, which phase, current milestone
- **Languages:** languages, programming languages, what languages, which languages, language
- **Type:** project type, type of project, what type, project kind

### Git
- **Branch:** branch, git branch, current branch, what branch, which branch
- **Status:** git status, git clean, git dirty, uncommitted, repo status, repository status, working tree
- **Operations:** git commit, git diff, git log, git add, commit, diff, log

### Memory
- **Recall:** remember, taught, teach, preference, recall, my name, what did i, do you remember

### Filesystem
- **Search:** where is, find, search, locate, find file, search for, locate, find class, find function
- **Read:** read, show, cat, view file, read file, show file, view
- **Write:** write, create, modify, edit, update file, write file, create file, edit file

### Knowledge
- **Conceptual:** explain, what is, how does, why, concept, tell me about, describe

### Execution
- **Tasks:** install, setup, configure, build, deploy, changed, review repository, summarize project, execute, run, perform, what changed

---

## Integration Points

### 1. Chat Integration
**File:** `chat.py` (when created)  
**Integration:** Use CapabilityLayer.handle() instead of direct LLM calls  
**Benefit:** Unified routing for all queries

### 2. Planner Integration
**File:** `agents/planner.py`  
**Current:** Planner receives world state but doesn't consult capability router  
**Future:** Planner asks CapabilityRouter which tools to use  
**Benefit:** Planner plans only when planning is required

### 3. ProjectContext Sharing
**File:** `core/project_context.py`  
**Current:** Instantiated per-use  
**Status:** Accessible by Planner, Chat, CapabilityRouter, Reflection, Memory  
**Benefit:** Single source of truth for project understanding

### 4. WorldState Direct Access
**File:** `core/world.py`  
**Current:** Passed to Planner  
**Status:** Directly queryable by CapabilityExecutor  
**Benefit:** No shell invocation for system state queries

---

## Performance Characteristics

| Capability Category | Typical Latency | Bottleneck |
|--------------------|--------------------|------------|
| System State | <10ms | Memory access |
| Workspace | <10ms | File metadata read |
| Git (state) | <10ms | Memory access |
| Memory | 50-100ms | Database query |
| Filesystem (read) | 10-50ms | Disk I/O |
| Filesystem (search) | 100-500ms | Grep operation |
| Knowledge (LLM) | 500-2000ms | LLM latency |
| Execution (Pipeline) | 1000-10000ms | Tool execution + LLM |

---

## Future Expansion

### Adding New Capabilities

1. **Define metadata** in `CapabilityRegistry._register_core_capabilities()`
   - Choose appropriate category
   - Declare owner and authoritative source
   - Specify requirements (planner, executor, LLM, tools)
   - Set latency category
   - Add keywords and synonyms

2. **Implement executor** in `CapabilityExecutor`
   - Add category-specific execution method
   - Delegate to owning subsystem
   - Return structured evidence

3. **Never duplicate** existing subsystem functionality
   - Reuse Memory, Planner, Executor, Observers, Tools
   - Integration, not reimplementation

### Example: Adding Browser Capability

```python
# 1. Register capability
self.register(CapabilityMetadata(
    name="browser_navigate",
    category=CapabilityCategory.BROWSER,
    description="Navigate to URLs and interact with web pages",
    owner_module="tools.browser",
    authoritative_source="browser tool",
    requires_planner=False,
    requires_executor=True,
    requires_llm=False,
    requires_tools=["browser_navigate", "browser_click"],
    latency=LatencyCategory.MODERATE,
    keywords=["navigate", "open url", "browse", "click"],
    synonyms=["go to", "visit", "open page"]
))

# 2. Implement executor
async def _execute_browser(self, capability, query):
    # Delegate to browser tool
    return await invoke_browser_tool(capability, query)
```

---

## Summary

Friday's Capability Layer provides:

✅ **Metadata-driven routing** — Router reasons over capability characteristics  
✅ **Ownership boundaries** — Each capability has a single authoritative source  
✅ **No duplication** — Always delegates to existing subsystems  
✅ **Evidence-first** — Grounded facts before LLM synthesis  
✅ **Performance awareness** — Prefer instant over slow capabilities  
✅ **Extensibility** — Add capabilities without modifying router logic

**The LLM is a synthesizer, not a source of truth.**
