"""Orchestrator: the kernel that processes every Intent flowing through Friday."""

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

            # Log what we received
            print(
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
                # Chat path unchanged
                model_t0 = time.perf_counter()
                response = await call_model(text)
                model_dt = time.perf_counter() - model_t0
                intent.metadata = {"model_time": model_dt}
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
