"""Orchestrator: the kernel that processes every Intent flowing through Friday."""

import sys
import asyncio
from .bus import EventBus
from .intent import Intent
from .model_client import call_model


class Orchestrator:
    """Consumes Intents from the bus and dispatches responses."""

    def __init__(self, bus: EventBus):
        self.bus = bus

    async def run(self) -> None:
        """Main loop: consume Intents and respond to each one."""
        import time
        from core.run import PipelineRun
        from core.pipeline import run_pipeline

        while True:
            intent = await self.bus.consume()

            # Log what we received (debug only)
            from core.output_mode import log_debug
            log_debug(
                f"[orchestrator] got intent {intent.id} ({intent.kind}) "
                f"from {intent.source}: {intent.payload}"
            )

            # Route based on intent kind
            text = intent.payload.get("text", "")

            if intent.kind == "task":
                # Task execution pipeline
                pipeline_run = PipelineRun(intent=intent)
                try:
                    response = await run_pipeline(pipeline_run)
                except Exception as e:
                    response = f"Pipeline execution crashed: {e}"
            elif intent.kind == "chat":
                import time as _time
                from core.fast_path import handle_fast_path
                from core.capability_layer import CapabilityLayer
                from memory.manager import MemoryManager
                from core.output_mode import log_verbose, log_debug

                # Try fast path first (greetings, simple queries)
                fast_response = handle_fast_path(text)
                if fast_response:
                    response = fast_response
                    log_debug(f"[orchestrator] fast path: {text[:50]}")
                    intent.metadata = {"fast_path": True}
                else:
                    t_start = _time.perf_counter()

                    # Phase 10: Capability Layer
                    # Route through capability layer (primary routing mechanism)
                    capability_layer = CapabilityLayer()

                    t_capability = _time.perf_counter()
                    response, capability_metadata = await capability_layer.handle(text, verbose=True)
                    dt_capability = _time.perf_counter() - t_capability

                    log_verbose(
                        f"[chat] capability={capability_metadata.get('capability')} "
                        f"category={capability_metadata.get('category')} "
                        f"execution_path={capability_metadata.get('execution_path')} "
                        f"latency={capability_metadata.get('latency_ms', 0):.2f}ms"
                    )

                    # Memory extraction (background)
                    memory_manager = MemoryManager()
                    will_extract = memory_manager.should_extract(text)
                    if will_extract:
                        asyncio.create_task(memory_manager.process_chat(intent.id, text, response))

                    total_dt = _time.perf_counter() - t_start
                    log_verbose(
                        f"[chat] capability={dt_capability:.2f}s "
                        f"memory_extraction={'queued' if will_extract else 'skipped'} "
                        f"total={total_dt:.2f}s"
                    )
                    intent.metadata = {
                        "capability": capability_metadata.get('capability'),
                        "category": capability_metadata.get('category'),
                        "execution_path": capability_metadata.get('execution_path'),
                    }
            elif intent.kind == "hybrid":
                # Phase 10: Hybrid through Capability Layer
                # Let capability layer decide whether to use pipeline or direct synthesis
                from core.capability_layer import CapabilityLayer

                capability_layer = CapabilityLayer()
                response, capability_metadata = await capability_layer.handle(text, verbose=True)

                intent.metadata = {
                    "capability": capability_metadata.get('capability'),
                    "category": capability_metadata.get('category'),
                    "execution_path": capability_metadata.get('execution_path'),
                }
            else:
                response = f"Friday heard: {text}"

            # Send response back to whoever submitted this Intent
            if intent.response_future and not intent.response_future.done():
                intent.response_future.set_result(response)
