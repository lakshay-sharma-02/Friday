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
                import time as _time
                from memory.manager import MemoryManager
                memory_manager = MemoryManager()

                # Retrieve relevant memories
                t_search = _time.perf_counter()
                memory_results = await asyncio.to_thread(memory_manager.search, text, limit=5)
                dt_search = _time.perf_counter() - t_search

                # Build explicit, typed long-term memory sections.
                # Episodic memories are run-history JSON and are not injected into chat.
                # Field names come straight from the retriever (content/type), not the
                # legacy shim (text/note_source) — a prior mismatch made injection a no-op.
                SECTION_ORDER = [
                    ("Teaching", "Teaching (Highest Priority)"),
                    ("Preference", "Preference"),
                    ("Knowledge", "Knowledge"),
                    ("Lesson", "Lessons"),
                    ("Fact", "Facts"),
                ]
                grouped = {t: [] for t, _ in SECTION_ORDER}
                for r in memory_results:
                    mtype = r.get("type")
                    content = r.get("content", "")
                    if mtype in grouped and content:
                        grouped[mtype].append(content)

                prompt = text
                if any(grouped.values()):
                    sections = ["LONG TERM MEMORY"]
                    for mtype, header in SECTION_ORDER:
                        items = grouped[mtype]
                        if not items:
                            continue
                        sections.append("")
                        sections.append(header)
                        if mtype == "Teaching":
                            sections.append("Teaching overrides default model knowledge.")
                        for c in items:
                            sections.append(f"- {c}")
                    sections.append("")
                    sections.append("------")
                    sections.append(
                        "Follow any rules, preferences, or teachings above your prior knowledge."
                    )
                    sections.append(f"User: {text}")
                    prompt = "\n".join(sections)

                model_t0 = _time.perf_counter()
                response = await call_model(prompt, enable_thinking=False)
                model_dt = _time.perf_counter() - model_t0

                # Decide extraction (deterministic gate) and run it in the background.
                will_extract = memory_manager.should_extract(text)
                if will_extract:
                    asyncio.create_task(memory_manager.process_chat(intent.id, text, response))

                total_dt = _time.perf_counter() - t_search
                print(
                    f"[chat] memory_search={dt_search:.2f}s "
                    f"chat_generation={model_dt:.2f}s "
                    f"memory_extraction={'queued' if will_extract else 'skipped'} "
                    f"total={total_dt:.2f}s",
                    file=sys.stderr,
                )
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
