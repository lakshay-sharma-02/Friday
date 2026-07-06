# Friday Phase 2: Real Execution Runtime

## Implementation Complete

Friday has been transformed from a chat bot into an AI runtime with real execution and objective verification.

### Architecture

**Single LLM Call**: The planner is the only model invocation in the entire pipeline. Everything after planning is deterministic code execution.

**Reality-Based Verification**: Success/failure is determined by:
- Exit codes
- Filesystem state
- Subprocess output
- Exceptions

No model judges results. Reality is the verifier.

### Components Built

1. **Pipeline State** (`core/run.py`)
   - Tracks plan, execution log, retry count, status
   - Each log entry records tool, args, timing, output, exit_code, success

2. **Tool Registry** (`tools/registry.py`)
   - Single source of truth for all tools
   - Maps tool names to handlers, descriptions, argument schemas

3. **Tool Implementations**
   - `tools/shell.py` - Execute shell commands
   - `tools/files.py` - Read/write files
   - `tools/git.py` - Git operations
   - All handlers are synchronous, return dicts, never crash

4. **Permissions** (`core/permissions.py`)
   - Tier 0: Execute immediately
   - Tier 1: Prompt user (auto-approve in non-interactive mode)
   - Loaded once from `config/permissions.yaml`

5. **Planner** (`agents/planner.py`)
   - Single LLM call that outputs JSON plan
   - Uses only tools from registry
   - No markdown, no prose, just valid JSON

6. **Executor** (`core/executor.py`)
   - Generic dispatch through registry
   - Validates plan steps
   - Records timing and results
   - Never crashes on tool failure

7. **Pipeline** (`core/pipeline.py`)
   - Plan → Execute → Check reality → Retry if failed
   - Retry context includes actual failure output
   - Max 2 retries, then stop

8. **Orchestrator Integration**
   - Chat path: unchanged
   - Task path: `task:` prefix triggers pipeline

### Test Results

✅ **Test 1**: Simple shell command
```
task: run echo hello world
→ Plan: 1 step
→ Execution: success
→ Output: hello world
```

✅ **Test 2**: Command not found with retry
```
task: run foobar123
→ Plan: 1 step (shell foobar123)
→ Execution: exit_code=127 (command not found)
→ Retry: planner gets failure context
→ Result: no valid alternative plan after retry
→ Clean failure, no crash
```

### Design Principles Followed

- Files are short and focused
- No abstractions for hypothetical use
- Simple functions, dataclasses, registry
- Direct dispatch, no dependency injection
- Reality determines truth, not models
- Extensibility through registry pattern

### Adding New Tools

To add a tool:
1. Write handler function in `tools/`
2. Add entry to `TOOL_REGISTRY`
3. Add permission tier to `config/permissions.yaml`

Done. No other changes needed.

### Future Foundation

This phase establishes the runtime foundation. Every future capability builds on this:
- Models hypothesize
- Tools execute
- Reality verifies
- System learns

Friday is now an operating system for AI execution.
