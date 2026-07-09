# Friday Request Tracing System

Complete end-to-end request tracing with full observability into every LLM request.

## Quick Start

### Enable Tracing

```bash
export FRIDAY_TRACE=1
```

### Run Friday with Tracing

```bash
./main.py
```

### View Traces

```bash
# Show latest trace summary
./friday_trace.py trace

# Full debug view
./friday_trace.py debug-last

# Complete payload
./friday_trace.py payload

# Search for keywords
./friday_trace.py search requests pip install

# List all traces
./friday_trace.py list
```

## What Gets Traced

Every trace captures:

- **Routing**: Which capability handled the request and why
- **Evidence**: All collected evidence with sources
- **Memory**: Retrieved/selected/rejected memories with scores
- **Workspace**: Complete project snapshot
- **Prompts**: Exact system prompt, evidence block, user prompt
- **Payload**: **Complete final payload sent to model** (no truncation)
- **Response**: Raw output, tokens, latency
- **Pipeline**: All stages with timing
- **Contamination**: Automatic context leak detection

## CLI Commands

```bash
./friday_trace.py trace          # Latest trace summary
./friday_trace.py debug-last     # Full debug + auto-search
./friday_trace.py payload        # Complete payload
./friday_trace.py search <words> # Search payload
./friday_trace.py list           # List all traces
```

## Debugging Workflow

When investigating issues:

```bash
# 1. Enable tracing
export FRIDAY_TRACE=1

# 2. Reproduce the issue
# (run the problematic query)

# 3. Debug
./friday_trace.py debug-last

# 4. Search for suspicious keywords
./friday_trace.py search requests pip uv install failed

# 5. Inspect complete payload
./friday_trace.py payload
```

## Context Leak Detection

Automatically detects:
- Conversation history markers
- Previous task markers
- Planner output leakage
- Unintended memory sections

## Architecture

- **Zero overhead when disabled** (default)
- **~1-5ms overhead when enabled**
- **Non-invasive**: No changes to pipeline logic
- **Local storage**: `logs/traces/`
- **Complete payload capture**: No truncation or summarization

## Files

```
core/trace.py                    - Core infrastructure
core/trace_integration.py        - Integration helpers
core/trace_wrapper.py            - Request wrapper
core/trace_viewer.py             - CLI viewer
core/capability_router_traced.py - Traced router
core/model_client_traced.py      - Traced model client
agents/planner_traced.py         - Traced planner
friday_trace.py                  - Convenience CLI
tests/test_trace.py              - Unit tests
tests/test_trace_integration.py  - Integration tests
```

## Testing

```bash
# Run trace tests
pytest tests/test_trace.py -v

# Run integration tests
pytest tests/test_trace_integration.py -v

# Run demo
python demo_tracing.py
```

## Documentation

- **TRACING.md** - Complete documentation
- **PHASE11_TRACING_COMPLETE.md** - Technical summary
- **PHASE11_DELIVERY.md** - Delivery summary

## Success Criteria

✅ Every request is fully inspectable  
✅ Can prove exactly what model received  
✅ Can identify source of any information  
✅ Can detect model fabrication  
✅ Automatic context leak detection  
✅ Zero overhead when disabled  
✅ Non-invasive implementation  

## Example Output

```
================================================================================
TRACE: 20260709_132410_835116
Time: 2026-07-09T13:24:10.835179
Success: True
Total Latency: 0.000s
================================================================================

Original Prompt: analyze this repository

Capability: repository_analysis
Operation: ANALYZE
Confidence: 0.95

================================================================================
PIPELINE STAGES
================================================================================

capability_routing: 0.000s
memory_search: 0.000s
evidence_collection: 0.000s
llm_call: 0.000s
```

## Benefits

1. **Complete Observability** - Every request fully inspectable
2. **Deterministic Debugging** - No more guessing
3. **Context Leak Detection** - Automatic contamination detection
4. **Validation Ready** - Can prove evidence precedence
5. **Zero Default Overhead** - Only pays cost when enabled
6. **Reproducible** - Traces can be saved and replayed
7. **Non-Invasive** - No changes to core logic
