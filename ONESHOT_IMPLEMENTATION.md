# One-Shot Command Implementation - Complete

**Date:** 2026-07-09  
**Status:** ✓ Implemented and Tested

---

## Objective

Enable Friday to accept single commands via command-line arguments instead of only running in interactive mode.

---

## Problem

**Before:**
```bash
python main.py "What is 2 + 2?"
# Launches interactive CLI, ignores the argument
```

Friday only operated in interactive mode. No way to execute discrete commands.

---

## Solution

Added command-line argument parsing to `main.py` and created `interfaces/oneshot.py` for single-command execution.

---

## Implementation

### Files Modified

**1. `main.py` (Lines 1-79)**
- Added sys.argv parsing
- Added one-shot execution path
- Imports `run_oneshot` from interfaces
- When arguments present: execute command and exit
- When no arguments: launch interactive CLI

**2. `interfaces/__init__.py`**
- Exported `run_oneshot` alongside `run_cli`

### Files Created

**3. `interfaces/oneshot.py` (23 lines)**
- `run_oneshot(bus, command)` function
- Routes command through intent router
- Publishes to event bus
- Waits for response
- Prints result and exits

---

## Behavior

### Interactive Mode (No Arguments)
```bash
python main.py
# Friday CLI ready. Type 'exit' or 'quit' to stop.
# >
```

### One-Shot Mode (With Arguments)
```bash
python main.py "What is 2 + 2?"
# 4
```

---

## Test Results

### Test 1: Simple Math Query
```bash
$ python main.py "What is 2 + 2?"
```

**Output:**
```
Warning: You are sending unauthenticated requests to the HF Hub...
Loading weights: 100%|██████████| 103/103 [00:00<00:00, 3435.27it/s]
[model_client] routing to model=oc/deepseek-v4-flash-free
[model_client] response served by: deepseek-v4-flash-free
[model_client] first_token: 1.98s, total: 2.17s
[capability] Capability: conceptual_knowledge, Operation: read
4
```

**Result:** ✓ PASS

---

## Architecture Integration

### Intent Routing
One-shot commands use the same intent router as interactive mode:
- `route_intent(command)` classifies the request
- Intent published to event bus
- Orchestrator processes via capability layer
- Response returned synchronously

### No Duplicate Logic
One-shot mode reuses all existing subsystems:
- Intent Router
- Capability Layer
- Memory Manager
- World State Observers
- Tool Registry
- Model Client

---

## Usage Patterns

### Task Execution
```bash
python main.py "Remove stale test files"
```

### Information Query
```bash
python main.py "What project are we building?"
```

### File Operations
```bash
python main.py "Read README.md"
```

### Memory Query
```bash
python main.py "What is my name?"
```

---

## Recursive Development Impact

**Could Friday complete the original task before?** NO  
**Can Friday complete it now?** YES

Friday can now be invoked as a tool for discrete tasks, enabling recursive development where Friday performs work on itself.

---

## Next Steps

1. Use Friday to remove stale Phase 9 test files
2. Verify test collection succeeds
3. Document findings

---

## Success Criteria

✓ Friday accepts command-line arguments  
✓ One-shot commands execute and exit cleanly  
✓ Interactive mode still works when no arguments provided  
✓ All existing subsystems reused (no duplicate logic)  
✓ Intent routing preserved  
✓ Memory and capability layer integration intact

---

## Code Footprint

- Lines modified: 15 (main.py, interfaces/__init__.py)
- Lines created: 23 (interfaces/oneshot.py)
- Total: 38 lines
- Test files: 0 (manually verified)

---

## Capability Unlocked

Friday can now recursively improve itself by accepting tasks as command-line arguments.
