"""Traced model client - wraps model_client with request tracing."""

import time
from core.model_client import call_model as _original_call_model
from core.trace import get_current_trace, TraceStage


async def call_model_traced(text: str, route: str = "cheap_chat",
                            enable_thinking: bool = True,
                            stream_to_stdout: bool = True) -> str:
    """Traced wrapper around call_model."""
    trace = get_current_trace()

    if trace is None:
        # No trace context, call original
        return await _original_call_model(text, route, enable_thinking, stream_to_stdout)

    # Start LLM stage
    trace.start_stage(TraceStage.LLM_CALL, input_data={
        "route": route,
        "enable_thinking": enable_thinking,
        "prompt_length": len(text)
    })

    start_time = time.perf_counter()

    try:
        response = await _original_call_model(text, route, enable_thinking, stream_to_stdout)
        latency = time.perf_counter() - start_time

        # Record the call in trace
        from core.model_client import SYSTEM_PROMPT
        trace.set_prompt_trace(
            system_prompt=SYSTEM_PROMPT,
            evidence_block="",  # Will be set separately if evidence exists
            user_prompt=text,
            final_payload=f"SYSTEM:\n{SYSTEM_PROMPT}\n\nUSER:\n{text}",
            token_estimate=len(text) // 4
        )

        trace.set_model_response(
            raw_output=response,
            parsed_output=None,
            latency=latency
        )

        trace.end_stage(output_data={
            "response_length": len(response),
            "latency_seconds": latency
        })

        return response

    except Exception as e:
        trace.end_stage(errors=[str(e)])
        raise


# Export for use when tracing is enabled
__all__ = ["call_model_traced"]
