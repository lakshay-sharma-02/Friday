"""Integration point for request tracing in Friday's pipeline.

This module wires tracing into the main request flow without modifying
existing pipeline logic.
"""

import sys
import os
from typing import Optional
from core.trace import start_trace, end_trace, get_current_trace, save_current_trace


ENABLE_TRACING = os.getenv("FRIDAY_TRACE", "0") == "1"


async def trace_request(prompt: str, handler_func):
    """Wrap a request handler with tracing."""

    if not ENABLE_TRACING:
        # Tracing disabled, call handler directly
        return await handler_func()

    # Start trace
    trace_ctx = start_trace(prompt)

    try:
        # Execute handler
        result = await handler_func()

        # Finalize trace
        trace = end_trace(success=True)

        # Save trace to disk
        if trace:
            trace_path = trace.save()
            print(f"[trace] saved to {trace_path}", file=sys.stderr)

            # Print contamination warnings
            if trace.contamination_sources:
                print(f"[trace] ⚠ contamination detected: {trace.contamination_sources}", file=sys.stderr)

        return result

    except Exception as e:
        # Finalize trace with error
        trace = end_trace(success=False, error=str(e))

        # Save trace
        if trace:
            trace_path = trace.save()
            print(f"[trace] saved (failed) to {trace_path}", file=sys.stderr)

        raise


def is_tracing_enabled() -> bool:
    """Check if tracing is enabled."""
    return ENABLE_TRACING


def enable_tracing():
    """Enable tracing for this session."""
    global ENABLE_TRACING
    ENABLE_TRACING = True
    os.environ["FRIDAY_TRACE"] = "1"
    print("[trace] enabled", file=sys.stderr)


def disable_tracing():
    """Disable tracing for this session."""
    global ENABLE_TRACING
    ENABLE_TRACING = False
    os.environ["FRIDAY_TRACE"] = "0"
    print("[trace] disabled", file=sys.stderr)
