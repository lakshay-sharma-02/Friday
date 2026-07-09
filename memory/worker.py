"""Background worker for embedding generation."""
import threading
import queue
import time
import sys
from .store import MemoryStore
from .ranking import _ranker

class EmbeddingWorker:
    def __init__(self):
        self.queue = queue.Queue()
        self._thread = None
        self._running = False
        self._rebuild_state = {"total": 0, "processed": 0, "interrupted": False}
        
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        self._running = False
        if self._thread:
            self.queue.put(("STOP", None))
            self._thread.join(timeout=2.0)
            
    def enqueue(self, memory_id: str):
        self.queue.put(("EMBED", memory_id))
        
    def rebuild_all(self):
        self.queue.put(("REBUILD_ALL", None))
        
    def rebuild_single(self, memory_id: str):
        self.queue.put(("EMBED", memory_id))
        
    def delete_embedding(self, memory_id: str):
        self.queue.put(("DELETE", memory_id))
        
    def resume_rebuild(self):
        self.queue.put(("RESUME_REBUILD", None))
        
    def get_progress(self) -> dict:
        return self._rebuild_state
        
    def _run_loop(self):
        store = MemoryStore()  # Independent connection for background thread
        while self._running:
            try:
                action, payload = self.queue.get(timeout=1.0)
                if action == "STOP":
                    break
                elif action == "EMBED":
                    self._process_single(store, payload)
                elif action == "DELETE":
                    try:
                        _ranker.embedding_index.delete_embedding(payload)
                    except Exception as e:
                        print(f"[embedding_worker] Failed to delete embedding {payload}: {e}", file=sys.stderr)
                elif action == "EMBED_RETRY":
                    memory_id, retry_count = payload
                    self._process_single(store, memory_id, retry_count)
                elif action == "REBUILD_ALL":
                    self._process_rebuild(store, resume=False)
                elif action == "RESUME_REBUILD":
                    self._process_rebuild(store, resume=True)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[embedding_worker] Loop error: {e}", file=sys.stderr)
                time.sleep(1.0)
                
    def _process_single(self, store: MemoryStore, memory_id: str, retry_count: int = 0):
        try:
            mem = store.get_memory(memory_id)
            if not mem:
                return
            
            content = mem.get("content", "")
            if mem["type"] == "Episodic":
                try:
                    import json
                    c = json.loads(content)
                    text = c.get("intent_text", "")
                except Exception:
                    text = content
            else:
                text = content
                
            _ranker.embedding_index.generate_and_store(memory_id, text)
            
        except Exception as e:
            print(f"[embedding_worker] Failed to generate embedding for {memory_id}: {e}", file=sys.stderr)
            if retry_count < 3:
                # Retry later without interrupting user request
                time.sleep(0.5 * (retry_count + 1))
                self.queue.put(("EMBED_RETRY", (memory_id, retry_count + 1)))
                
    def _process_rebuild(self, store: MemoryStore, resume: bool = False):
        print(f"[embedding_worker] {'Resuming' if resume else 'Starting'} bulk rebuild...", file=sys.stderr)
        mems = store.get_memories()
        
        if not resume or self._rebuild_state["total"] == 0:
            self._rebuild_state["total"] = len(mems)
            self._rebuild_state["processed"] = 0
            
        self._rebuild_state["interrupted"] = False
        start_idx = self._rebuild_state["processed"]
        
        for i in range(start_idx, len(mems)):
            if not self._running:
                print("[embedding_worker] Bulk rebuild interrupted.", file=sys.stderr)
                self._rebuild_state["interrupted"] = True
                break
                
            self._process_single(store, mems[i]["id"])
            self._rebuild_state["processed"] += 1
            
            if self._rebuild_state["processed"] % 10 == 0 or self._rebuild_state["processed"] == self._rebuild_state["total"]:
                p = self._rebuild_state["processed"]
                t = self._rebuild_state["total"]
                print(f"[embedding_worker] Rebuild progress: {p}/{t} ({p/t*100:.1f}%)", file=sys.stderr)
                
        if self._rebuild_state["processed"] == self._rebuild_state["total"]:
            print("[embedding_worker] Bulk rebuild complete.", file=sys.stderr)

# Global singleton worker
_worker = EmbeddingWorker()

def get_worker() -> EmbeddingWorker:
    return _worker
