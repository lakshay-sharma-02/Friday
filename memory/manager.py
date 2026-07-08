import sys
import json
from .store import MemoryStore
from .retriever import MemoryRetriever
from .worker import get_worker
from core.run import PipelineRun

class MemoryManager:
    """Orchestrates memory admission, promotion, and retrieval."""
    
    def __init__(self):
        self.store = MemoryStore()
        self.retriever = MemoryRetriever(self.store)

    def search(self, query: str, limit: int = 5):
        return self.retriever.search(query, limit)

    def extract_lesson(self, planner_output: str) -> tuple[str, str | None]:
        """Extract LESSON: from planner output. Returns (cleaned_output, lesson)."""
        lesson = None
        lines = planner_output.strip().split("\n")
        if lines and lines[-1].startswith("LESSON:"):
            lesson = lines[-1][7:].strip()
            cleaned = "\n".join(lines[:-1]).strip()
            return cleaned, lesson
        return planner_output, None

    def process_run(self, run: PipelineRun, planner_lesson: str | None):
        """Process pipeline run for history and admission into episodic memory."""
        # History records everything
        try:
            self.store.append_history(run)
        except Exception as e:
            print(f"[memory] failed to append history: {e}", file=sys.stderr)

        # Admission Gate for Episodic Memory
        # Only store if it's not a routine successful command or if it has a lesson
        is_routine = run.status == "completed" and run.retry_count == 0 and not planner_lesson
        
        # We consider a run worth remembering if:
        # - It failed (we learn from failures)
        # - It required retries (struggle implies learning)
        # - It generated an explicit lesson
        # - Or it was a complex task (could be inferred, but let's use the above)
        should_promote = not is_routine
        
        if should_promote:
            try:
                run_id = self.store.put_run(run)
                if run_id:
                    get_worker().enqueue(run_id)
            except Exception as e:
                print(f"[memory] failed to promote run to episodic memory: {e}", file=sys.stderr)

        # Process Lesson
        if planner_lesson:
            try:
                note_id = self.store.add_note(planner_lesson, "lesson", run.intent.id)
                if note_id:
                    get_worker().enqueue(note_id)
            except Exception as e:
                print(f"[memory] failed to store lesson: {e}", file=sys.stderr)

    _EXTRACTION_TRIGGERS = (
        "remember", "always", "never", "from now on", "my preference",
        "don't", "dont", "actually", "i always", "i never",
        "i prefer", "keep in mind", "note:", "teach:", "i want you to",
        "please remember", "i like", "i dislike", "i hate", "i use",
    )

    def should_extract(self, user_text: str) -> bool:
        """Deterministic gate: only invoke LLM memory extraction when the user
        text plausibly teaches something. No model call otherwise."""
        t = user_text.strip().lower()
        if not t:
            return False
        if any(t.startswith(trigger) or f" {trigger}" in t
               for trigger in self._EXTRACTION_TRIGGERS):
            # Guard: "i use" must not be the tail of "should i use" / "do i use".
            if "should i use" in t or "do i use" in t:
                return False
            return True
        return False

    async def process_chat(self, intent_id: str, user_text: str, ai_response: str):
        """Analyze chat for memory creation (gated by should_extract)."""
        """Analyze chat for memory creation."""
        from core.model_client import call_model

        # Admission gate: skip the extraction LLM entirely for chit-chat.
        if not self.should_extract(user_text):
            return

        prompt = f"""Analyze this chat exchange between a user and an AI assistant.
Does the user explicitly teach the AI a rule, state a strong preference, or state an important permanent fact about the project or themselves?

User: {user_text}
AI: {ai_response}

If yes, output ONLY a valid JSON object with the following schema, and NOTHING ELSE:
{{
  "type": "Teaching" | "Preference" | "Fact" | "Knowledge" | "Lesson",
  "content": "<concise summary of what must be remembered>"
}}
If no, output an empty JSON object: {{}}
"""
        try:
            # Store original system prompt
            import core.model_client as client_module
            original_prompt = client_module.SYSTEM_PROMPT
            client_module.SYSTEM_PROMPT = "You are a data extraction system. Output only valid JSON."
            
            result = await call_model(prompt)
            
            # Restore system prompt
            client_module.SYSTEM_PROMPT = original_prompt
            
            # clean up markdown fences
            if result.startswith("```"):
                lines = result.split("\n")
                result = "\n".join(lines[1:-1]) if len(lines) > 2 else result
                result = result.removeprefix("json").strip()
            
            data = json.loads(result)
            if data and data.get("content"):
                mem_type = data.get("type", "Fact")
                if mem_type not in self.store.VALID_TYPES:
                    mem_type = "Fact"
                    
                note_id = self.store.store_memory(
                    memory_type=mem_type,
                    content=data["content"],
                    importance=0.8,
                    source="taught",
                    run_id=intent_id
                )
                if note_id:
                    get_worker().enqueue(note_id)
        except Exception as e:
            print(f"[memory] failed to extract chat memory: {e}", file=sys.stderr)

    def change_embedding_model(self, model_name: str):
        """Update the embedding model and trigger a full rebuild."""
        from .ranking import _ranker
        _ranker.embedding_index.backend.model_name = model_name
        _ranker.embedding_index.backend._initialized = False
        _ranker.embedding_index.backend.initialize()
        get_worker().rebuild_all()

    def get_rebuild_progress(self) -> dict:
        """Get the current progress of the embedding rebuild."""
        return get_worker().get_progress()

    def resume_rebuild(self):
        """Resume an interrupted rebuild."""
        get_worker().resume_rebuild()
