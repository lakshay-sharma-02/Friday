# Request Tracing - Complete Observability

## Overview

Friday now has comprehensive request tracing that provides full observability into every LLM request and pipeline execution. Every request can be inspected to understand exactly what evidence, memory, and context was provided to the model.

## Purpose

The tracing system eliminates guessing by making every request fully inspectable:

- **Evidence tracking**: What evidence was collected and from where
- **Memory tracking**: Which memories were retrieved, selected, and rejected
- **Prompt inspection**: Complete system prompt, evidence block, and user prompt
- **Payload verification**: The exact final payload sent to the model
- **Context leak detection**: Automatic detection of unintended context contamination
- **Pipeline visibility**: Timing and data flow through each stage

## Architecture

### Core Components

1. **`core/trace.py`**: Core tracing data structures
   - `RequestTrace`: Complete trace of a single request
   - `TraceContext`: Context manager for building traces
   - `TraceStage`: Pipeline stages (routing, memory, evidence, planning, execution, LLM)
   - `EvidenceTrace`, `MemoryTrace`, `PromptTrace`, `ModelResponseTrace`: Specialized traces

2. **`core/trace_integration.py`**: Integration helpers
   - Functions to record routing decisions, memory retrieval, evidence collection
   - Decorators to automatically trace pipeline stages

3. **`core/trace_wrapper.py`**: Main request wrapper
   - `trace_request()`: Wraps request handlers with tracing
   - Environment variable control: `FRIDAY_TRACE=1`

4. **`core/trace_viewer.py`**: CLI viewer
   - Display trace summaries, evidence, memory, prompts, contamination

5. **`friday_trace.py`**: Convenience CLI
   - `friday trace`: Show latest trace summary
   - `friday debug-last`: Full debug view with auto-search
   - `friday payload`: Show complete payload
   - `friday search <keywords>`: Search payload for keywords
   - `friday list`: List all traces

### Traced Components

- **Capability Router** (`core/capability_router_traced.py`)
- **Planner** (`agents/planner_traced.py`)
- **Model Client** (`core/model_client_traced.py`)

## Usage

### Enable Tracing

Set the environment variable:

```bash
export FRIDAY_TRACE=1
```

Or enable in the session:

```python
from core.trace_wrapper import enable_tracing
enable_tracing()
```

### View Traces

```bash
# Show summary of latest trace
./friday_trace.py trace

# Full debug view with auto-search for suspicious keywords
./friday_trace.py debug-last

# Show complete payload sent to model
./friday_trace.py payload

# Search for specific keywords in payload
./friday_trace.py search requests pip install failed

# List all traces
./friday_trace.py list
```

### Programmatic Access

```python
from core.trace import start_trace, end_trace, get_current_trace

# Start tracing
ctx = start_trace("user prompt here")

# Record routing
ctx.set_routing("git_status", "READ", confidence=0.95)

# Record evidence
ctx.add_evidence("workspace", "project_type", "Python", confidence=1.0)

# Record memory
ctx.add_memory(
    memory_id="mem_123",
    memory_type="run",
    similarity=0.85,
    ranking=0.90,
    importance=0.7,
    relevance=0.8,
    content_preview="previous attempt",
    selected=True
)

# Start pipeline stage
ctx.start_stage(TraceStage.PLANNING, input_data={"task": "..."})

# End stage
ctx.end_stage(output_data={"plan_steps": 5})

# Finalize
trace = end_trace(success=True)

# Save to disk
trace.save()  # Saves to logs/traces/trace_<timestamp>.json
```

## Trace Contents

Each trace contains:

### Metadata
- `trace_id`: Unique identifier
- `timestamp`: When the request started
- `original_prompt`: User's original input
- `success`: Whether request succeeded
- `total_latency_seconds`: End-to-end latency

### Routing
- `intent_classification`: Classified intent
- `capability_selected`: Which capability handled the request
- `operation_selected`: Operation type (READ, EXECUTE, etc.)
- `capability_confidence`: Routing confidence score

### Evidence Collection
- `evidence[]`: Array of evidence items
  - `type`: Evidence source (memory, workspace, git, etc.)
  - `origin`: Where it came from
  - `size`: Size in bytes
  - `summary`: Preview of content
  - `confidence`: Confidence score

### Memory
- `memories_retrieved[]`: All memories found
- `memories_selected[]`: Memories passed to LLM
- `memories_rejected[]`: Memories filtered out
  - Each with similarity, ranking, importance, relevance scores
  - Rejection reason for rejected memories

### Workspace Snapshot
- `workspace_snapshot`: Current workspace state
- `project_metadata`: Project details
- `git_metadata`: Git state
- `documents_loaded`: Documentation files read

### Prompts
- `system_prompt`: Complete system prompt
- `evidence_block`: Structured evidence section
- `user_prompt`: Final user prompt
- `final_payload`: **Exact complete payload sent to model**
- `token_count_estimate`: Estimated tokens

### Model Response
- `raw_output`: Complete model response
- `parsed_output`: Structured output if applicable
- `input_tokens`: Actual input tokens (if available)
- `output_tokens`: Actual output tokens (if available)
- `latency_seconds`: Model response latency

### Pipeline Stages
- `stages[]`: Array of pipeline stages
  - Stage name (routing, memory, evidence, planning, execution, LLM)
  - Start/end times, duration
  - Input and output data
  - Errors if any

### Context Leak Detection
- `contains_conversation_history`: Boolean flag
- `contains_previous_tasks`: Boolean flag
- `contains_planner_output`: Boolean flag
- `contains_unintended_memory`: Boolean flag
- `contamination_sources[]`: List of detected contamination sources

## Context Leak Detection

The tracing system automatically detects potential context leaks by searching the final payload for suspicious patterns:

**Conversation History Markers**:
- "previous conversation"
- "earlier we discussed"
- "you mentioned"
- "in our last chat"

**Task History Markers**:
- "previous task"
- "last attempt"
- "earlier attempt"
- "previous execution"

**Planner Output Markers**:
- "planner output"
- "generated plan"
- "planning result"

**Unintended Memory Markers**:
- "memory:", "history:", "installs:", "past attempts:", "failed:", "failure:"
- Only flagged if they appear in the payload but NOT in the evidence block

When contamination is detected, the trace includes:
- Boolean flags for each contamination type
- List of specific contamination sources
- Automatic warnings in trace output

## Validation Workflow

When investigating issues (like hallucinations):

1. **Enable tracing**: `export FRIDAY_TRACE=1`
2. **Reproduce the issue**: Run the request that produced the problem
3. **Debug the trace**: `./friday_trace.py debug-last`
4. **Search for keywords**: `./friday_trace.py search requests pip uv install failed`
5. **Inspect the payload**: `./friday_trace.py payload`

This allows you to:
- Prove exactly what the model received
- Identify where unexpected information came from
- Detect if the model fabricated information not in the payload
- Verify evidence collection is working correctly
- Confirm memory retrieval is appropriate

## Isolated Replay

To determine if an issue is architectural or model-related:

1. Extract the final payload from the trace
2. Send it to the model in isolation (no conversation history, no additional memory)
3. Compare the response

If the model still produces the same output → model issue
If the model behaves correctly → architectural issue (contamination)

## Storage

Traces are saved to `logs/traces/` as JSON files:
- Format: `trace_<YYYYMMDD_HHMMSS_microseconds>.json`
- Complete, self-contained, reproducible
- Human-readable JSON with 2-space indentation

## Performance Impact

When tracing is **disabled** (default):
- **Zero overhead**: Tracing checks are simple boolean checks
- No data collection, no file writes

When tracing is **enabled**:
- **Minimal overhead**: ~1-5ms per request for trace construction
- File I/O is async and happens after response is sent
- Trace files are typically 5-50KB depending on evidence size

## Testing

Run the test suite:

```bash
pytest tests/test_trace.py -v
```

Tests cover:
- Trace lifecycle (start, stages, finalize)
- Evidence collection
- Memory tracking
- Routing decisions
- Contamination detection
- Serialization and persistence

## Example Trace

```json
{
  "trace_id": "20260709_075200_123456",
  "timestamp": "2026-07-09T07:52:00",
  "original_prompt": "analyze this repository",
  "capability_selected": "repository_analysis",
  "operation_selected": "ANALYZE",
  "capability_confidence": 0.95,
  "evidence": [
    {
      "type": "workspace",
      "origin": "project_type",
      "size": 6,
      "summary": "Python",
      "confidence": 1.0
    }
  ],
  "memories_selected": [
    {
      "memory_id": "run_456",
      "memory_type": "run",
      "similarity_score": 0.87,
      "content_preview": "Previous repository analysis attempt...",
      "selected": true
    }
  ],
  "prompt_trace": {
    "final_payload": "SYSTEM:\nYou are Friday...\n\nEVIDENCE:\n...\n\nUSER:\nanalyze this repository"
  },
  "contamination_sources": [],
  "success": true,
  "total_latency_seconds": 3.45
}
```

## Benefits

1. **Complete Observability**: Every request is fully inspectable
2. **No More Guessing**: Prove exactly what the model received
3. **Context Leak Detection**: Automatic detection of contamination
4. **Debugging**: Rapid diagnosis of hallucination vs payload issues
5. **Reproducibility**: Traces can be saved and replayed
6. **Zero Default Overhead**: Only pays cost when enabled
7. **Non-Invasive**: Doesn't modify core pipeline logic

## Future Enhancements

Potential additions:
- Real-time trace streaming to UI
- Trace diffing to compare requests
- Automatic anomaly detection
- Trace-based regression testing
- Integration with monitoring systems
