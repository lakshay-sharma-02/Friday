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
                from core.grounded_intelligence import GroundedIntelligence
                from core.world_manager import observe_world
                from core.project_context import ProjectContext
                from core.world import RuntimeState
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

                    # Phase 9: Grounded Intelligence
                    # Build world context for grounded answers
                    t_observe = _time.perf_counter()
                    world = await observe_world(cwd=".", runtime=RuntimeState())
                    dt_observe = _time.perf_counter() - t_observe

                    t_project = _time.perf_counter()
                    project_context = ProjectContext.from_workspace(world.workspace, ".")
                    dt_project = _time.perf_counter() - t_project

                    # Route to truth source and collect evidence
                    grounded = GroundedIntelligence()

                    t_route = _time.perf_counter()
                    routing_info = grounded.get_routing_info(text)
                    dt_route = _time.perf_counter() - t_route

                    log_verbose(
                        f"[chat] truth_source={routing_info['source']} "
                        f"confidence={routing_info['confidence']:.2f} "
                        f"bypass_planner={routing_info['bypass_planner']}"
                    )

                    # Answer using grounded intelligence
                    t_answer = _time.perf_counter()
                    response, decision = await grounded.answer(text, world, project_context)
                    dt_answer = _time.perf_counter() - t_answer

                    # Memory extraction (background)
                    memory_manager = MemoryManager()
                    will_extract = memory_manager.should_extract(text)
                    if will_extract:
                        asyncio.create_task(memory_manager.process_chat(intent.id, text, response))

                    total_dt = _time.perf_counter() - t_start
                    log_verbose(
                        f"[chat] observe={dt_observe:.2f}s project_context={dt_project:.2f}s "
                        f"route={dt_route:.2f}s answer={dt_answer:.2f}s "
                        f"memory_extraction={'queued' if will_extract else 'skipped'} "
                        f"total={total_dt:.2f}s"
                    )
                    intent.metadata = {
                        "truth_source": decision.source.value,
                        "grounded": True,
                    }
            elif intent.kind == "hybrid":
                # Hybrid execution pipeline: tools first, then LLM summary
                pipeline_run = PipelineRun(intent=intent)
                
                try:
                    summary_status = await run_pipeline(pipeline_run)
                    
                    # run_pipeline only returns a tiny string like "Task completed".
                    # We MUST extract the actual tool outputs from the execution_log for the LLM to read.
                    results_parts = [f"Pipeline Status: {summary_status}"]
                    for step_idx, entry in enumerate(pipeline_run.execution_log):
                        success_str = "SUCCESS" if entry.get('success') else "FAILED"
                        results_parts.append(f"--- Step {step_idx + 1} ({entry['tool']}) - {success_str} ---")
                        results_parts.append(f"Output: {entry.get('output', '')}\n")
                        
                    task_response = "\n".join(results_parts)
                    is_failed = pipeline_run.status == "failed" or "fail" in summary_status.lower()
                    
                except Exception as e:
                    task_response = f"CRITICAL PIPELINE FAILURE: {str(e)}"
                    is_failed = True
                
                model_t0 = time.perf_counter()
                
                # Force the model to not gloss over failures
                failure_instruction = ""
                if is_failed:
                    failure_instruction = (
                        "CRITICAL INSTRUCTION: The pipeline FAILED. You must report this failure plainly "
                        "and directly to the user. Do NOT reframe it as a success. Explain what went wrong "
                        "based on the execution results below."
                    )
                
                prompt = (
                    f"User asked: {text}\n\n"
                    f"{failure_instruction}\n\n"
                    f"Task execution results:\n{task_response}\n\n"
                    f"Please respond to the user based on these results."
                )
                response = await call_model(prompt)
                model_dt = time.perf_counter() - model_t0
                intent.metadata = {"model_time": model_dt}
            else:
                response = f"Friday heard: {text}"

            # Send response back to whoever submitted this Intent
            if intent.response_future and not intent.response_future.done():
                intent.response_future.set_result(response)
