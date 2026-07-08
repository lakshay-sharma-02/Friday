"""MemoryStore - SQLite-backed persistent storage with WAL mode for crash durability."""

import sqlite3
import json
import sys
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
from typing import Any


class MemoryStore:
    """Persistent storage for memories with crash-safe WAL mode."""

    VALID_TYPES = {"Fact", "Lesson", "Preference", "Knowledge", "Teaching", "Episodic"}

    def __init__(self, db_path: str = ".friday_memory.db"):
        """Initialize store and ensure schema exists."""
        self.db_path = db_path
        self._conn = None
        try:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._init_schema()
        except sqlite3.OperationalError as e:
            print(f"[memory] database unavailable: {e}", file=sys.stderr)
            print("[memory] falling back to stateless mode", file=sys.stderr)
        except Exception as e:
            print(f"[memory] store initialization failed: {e}", file=sys.stderr)

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        schema_path = Path(__file__).parent / "schema.sql"
        try:
            with open(schema_path, "r") as f:
                schema_sql = f.read()
            self._conn.executescript(schema_sql)
            self._conn.commit()
        except Exception as e:
            print(f"[memory] schema creation failed: {e}", file=sys.stderr)

    def store_memory(self, memory_type: str, content: str, importance: float = 0.0, 
                     project_tag: str = None, superseded_by: str = None, 
                     source: str = None, run_id: str = None) -> str:
        """Store a generic memory item."""
        if memory_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid memory type: {memory_type}")
            
        mem_id = run_id if run_id else str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        try:
            self._conn.execute(
                """
                INSERT INTO memories (id, type, content, importance, created_at, 
                                      last_accessed, reinforcement_count, project_tag, 
                                      superseded_by, source)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (mem_id, memory_type, content, importance, now, now, project_tag, superseded_by, source)
            )
            self._conn.commit()
            return mem_id
        except Exception as e:
            print(f"[memory] error storing memory: {e}", file=sys.stderr)
            return None

    def get_memory(self, mem_id: str) -> dict | None:
        """Fetch a memory by ID."""
        try:
            cursor = self._conn.execute("SELECT * FROM memories WHERE id = ?", (mem_id,))
            row = cursor.fetchone()
            if not row:
                return None
                
            now = datetime.now(timezone.utc).isoformat()
            self._conn.execute(
                """
                UPDATE memories 
                SET reinforcement_count = reinforcement_count + 1, last_accessed = ? 
                WHERE id = ?
                """,
                (now, mem_id)
            )
            self._conn.commit()
            return dict(row)
        except Exception as e:
            print(f"[memory] error fetching memory: {e}", file=sys.stderr)
            return None

    def get_memories(self, filters: dict = None) -> list[dict]:
        """Fetch memories optionally applying filters."""
        try:
            query = "SELECT * FROM memories"
            params = []
            
            if filters:
                clauses = []
                for k, v in filters.items():
                    clauses.append(f"{k} = ?")
                    params.append(v)
                if clauses:
                    query += " WHERE " + " AND ".join(clauses)
                    
            query += " ORDER BY created_at DESC"
            cursor = self._conn.execute(query, params)
            return [dict(row) for row in cursor]
        except Exception as e:
            print(f"[memory] error fetching memories: {e}", file=sys.stderr)
            return []

    # ---------------------------------------------------------
    # Backward Compatibility APIs for Pipeline & Tests
    # ---------------------------------------------------------

    def append_history(self, run: "PipelineRun") -> None:
        """Append a pipeline run to the raw history log."""
        from datetime import datetime, timezone
        import json
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Serialize run
        run_data = {
            "intent_id": run.intent.id,
            "intent_text": run.intent.payload.get("text", ""),
            "status": run.status,
            "retry_count": run.retry_count,
            "plan_risk_level": run.plan_risk_level
        }
        
        self._conn.execute(
            """INSERT INTO history (id, intent_id, run_status, timestamp, raw_data)
               VALUES (?, ?, ?, ?, ?)""",
            (run.intent.id, run.intent.id, run.status, now, json.dumps(run_data))
        )
        self._conn.commit()

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search delegates to MemoryRetriever.
        
        TODO(Phase 7C): Remove compatibility shim after Pipeline fully migrates to MemoryManager.
        """
        from .retriever import MemoryRetriever
        retriever = MemoryRetriever(self)
        results = retriever.search(query, limit)
        
        # Shim format
        formatted = []
        for r in results:
            if r["type"] == "Episodic":
                try:
                    c = json.loads(r["content"])
                    formatted.append({
                        "score": r.get("score", 0),
                        "source": "runs",
                        "id": r["id"],
                        "text": c.get("intent_text", ""),
                        "status": c.get("status", ""),
                        "created_at": r["created_at"]
                    })
                except Exception:
                    pass
            elif r["type"] in ("Lesson", "Teaching"):
                formatted.append({
                    "score": r.get("score", 0),
                    "source": "notes",
                    "id": r["id"],
                    "text": r["content"],
                    "note_source": "taught" if r["type"] == "Teaching" else "lesson",
                    "created_at": r["created_at"]
                })
        return formatted

    def stats(self) -> dict:
        """Compatibility shim for stats.
        
        TODO(Phase 7C): Remove compatibility shim after Pipeline fully migrates to MemoryManager.
        """
        try:
            stats = {}
            cursor = self._conn.execute("SELECT COUNT(*) as total FROM memories WHERE type = 'Episodic'")
            stats["total_runs"] = cursor.fetchone()["total"]
            
            cursor = self._conn.execute("SELECT importance, COUNT(*) as count FROM memories WHERE type = 'Episodic' GROUP BY importance")
            stats["runs_by_tier"] = {"HOT": 0, "WARM": 0, "COLD": 0}
            for row in cursor:
                t = "HOT" if row["importance"] > 0.8 else "WARM" if row["importance"] > 0.3 else "COLD"
                stats["runs_by_tier"][t] += row["count"]
                
            cursor = self._conn.execute("SELECT COUNT(*) as total FROM memories WHERE type IN ('Lesson', 'Teaching')")
            stats["total_notes"] = cursor.fetchone()["total"]
            
            cursor = self._conn.execute("SELECT importance, COUNT(*) as count FROM memories WHERE type IN ('Lesson', 'Teaching') GROUP BY importance")
            stats["notes_by_tier"] = {"HOT": 0, "WARM": 0, "COLD": 0}
            for row in cursor:
                t = "HOT" if row["importance"] > 0.8 else "WARM" if row["importance"] > 0.3 else "COLD"
                stats["notes_by_tier"][t] += row["count"]
                
            cursor = self._conn.execute("SELECT type, COUNT(*) as count FROM memories WHERE type IN ('Lesson', 'Teaching') GROUP BY type")
            stats["notes_by_source"] = {}
            for row in cursor:
                source_mapped = "lesson" if row["type"] == "Lesson" else "taught"
                stats["notes_by_source"][source_mapped] = row["count"]
                
            return stats
        except Exception as e:
            return {}

    def put_run(self, run: "PipelineRun") -> str:
        """Compatibility shim to store PipelineRun as Episodic memory.
        
        TODO(Phase 7C): Remove compatibility shim after Pipeline fully migrates to MemoryManager.
        """
        try:
            run_id = run.intent.id
            intent_text = run.intent.payload.get("text", "")
            
            content_dict = {
                "intent_text": intent_text,
                "intent_kind": run.intent.kind,
                "plan_json": json.dumps(run.plan) if run.plan else None,
                "execution_log_json": json.dumps(run.execution_log) if run.execution_log else None,
                "status": run.status
            }
            
            return self.store_memory(
                memory_type="Episodic",
                content=json.dumps(content_dict),
                importance=1.0,
                source="run",
                run_id=run_id
            )
        except Exception as e:
            print(f"[memory] error storing run via put_run: {e}", file=sys.stderr)
            return None

    def get_run(self, run_id: str) -> dict | None:
        """Compatibility shim to retrieve Episodic memory formatted like old runs.
        
        TODO(Phase 7C): Remove compatibility shim after Pipeline fully migrates to MemoryManager.
        """
        mem = self.get_memory(run_id)
        if not mem or mem["type"] != "Episodic":
            return None
            
        try:
            content = json.loads(mem["content"])
            return {
                "id": mem["id"],
                "intent_text": content.get("intent_text", ""),
                "intent_kind": content.get("intent_kind", ""),
                "plan_json": content.get("plan_json"),
                "execution_log_json": content.get("execution_log_json"),
                "status": content.get("status"),
                "created_at": mem["created_at"],
                "tier": "HOT" # Shim for legacy tests
            }
        except Exception:
            return None

    def add_note(self, content: str, source: str = "lesson", source_run_id: str | None = None) -> str:
        """Compatibility shim to store notes as Lesson or Teaching.
        
        TODO(Phase 7C): Remove compatibility shim after Pipeline fully migrates to MemoryManager.
        """
        mem_type = "Teaching" if source == "taught" else "Lesson"
        return self.store_memory(
            memory_type=mem_type,
            content=content,
            importance=0.5, # give lessons/teaching some baseline importance
            source=source
        )

    def get_all_runs(self) -> list[dict]:
        """Compatibility shim for old retrieve all runs logic.
        
        TODO(Phase 7C): Remove compatibility shim after Pipeline fully migrates to MemoryManager.
        """
        mems = self.get_memories({"type": "Episodic"})
        results = []
        for mem in mems:
            try:
                c = json.loads(mem["content"])
                results.append({
                    "id": mem["id"],
                    "intent_text": c.get("intent_text", ""),
                    "status": c.get("status", ""),
                    "created_at": mem["created_at"]
                })
            except Exception:
                pass
        return results

    def get_all_notes(self) -> list[dict]:
        """Compatibility shim for old retrieve all notes logic.
        
        TODO(Phase 7C): Remove compatibility shim after Pipeline fully migrates to MemoryManager.
        """
        mems = self.get_memories()
        results = []
        for mem in mems:
            if mem["type"] in ("Lesson", "Teaching"):
                results.append({
                    "id": mem["id"],
                    "content": mem["content"],
                    "source": mem["source"],
                    "created_at": mem["created_at"]
                })
        return results
        
    def promote(self, run_id: str) -> None:
        """Compatibility shim for importance promotion.
        
        TODO(Phase 7C): Remove compatibility shim after Pipeline fully migrates to MemoryManager.
        """
        try:
            mem = self.get_memory(run_id)
            if mem:
                new_imp = min(1.0, mem["importance"] + 0.5)
                self._conn.execute("UPDATE memories SET importance = ? WHERE id = ?", (new_imp, run_id))
                self._conn.commit()
        except Exception:
            pass

    def demote(self, run_id: str) -> None:
        """Compatibility shim for importance demotion.
        
        TODO(Phase 7C): Remove compatibility shim after Pipeline fully migrates to MemoryManager.
        """
        try:
            mem = self.get_memory(run_id)
            if mem:
                new_imp = max(0.0, mem["importance"] - 0.5)
                self._conn.execute("UPDATE memories SET importance = ? WHERE id = ?", (new_imp, run_id))
                self._conn.commit()
        except Exception:
            pass

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception as e:
                print(f"[memory] error closing connection: {e}", file=sys.stderr)
