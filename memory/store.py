"""MemoryStore - SQLite-backed persistent storage with WAL mode for crash durability."""

import sqlite3
import json
import sys
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
from typing import Any


class MemoryStore:
    """Persistent storage for runs and notes with crash-safe WAL mode."""

    def __init__(self, db_path: str = ".friday_memory.db"):
        """Initialize store and ensure schema exists.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._conn = None
        try:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            # Enable WAL mode for crash durability and concurrent read-while-write
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._init_schema()
        except Exception as e:
            print(f"[memory] error initializing store: {e}", file=sys.stderr)

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        schema_path = Path(__file__).parent / "schema.sql"
        try:
            with open(schema_path, "r") as f:
                schema_sql = f.read()
            self._conn.executescript(schema_sql)
            self._conn.commit()
        except Exception as e:
            print(f"[memory] error creating schema: {e}", file=sys.stderr)

    def put_run(self, run: "PipelineRun") -> str:
        """Store a pipeline run.

        Args:
            run: PipelineRun instance to store

        Returns:
            Run ID
        """
        try:
            run_id = run.intent.id
            intent_text = run.intent.payload.get("text", "")
            intent_kind = run.intent.kind
            plan_json = json.dumps(run.plan) if run.plan else None
            execution_log_json = json.dumps(run.execution_log) if run.execution_log else None
            status = run.status
            created_at = run.intent.created_at.isoformat()
            completed_at = datetime.now(timezone.utc).isoformat() if status in ("completed", "failed") else None

            self._conn.execute(
                """
                INSERT INTO runs (id, intent_text, intent_kind, plan_json, execution_log_json,
                                  status, created_at, completed_at, last_accessed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, intent_text, intent_kind, plan_json, execution_log_json,
                 status, created_at, completed_at, created_at)
            )
            self._conn.commit()
            return run_id
        except Exception as e:
            print(f"[memory] error storing run: {e}", file=sys.stderr)
            return None

    def get_run(self, run_id: str) -> dict | None:
        """Fetch a run by ID and update access tracking.

        Args:
            run_id: Run identifier

        Returns:
            Run data as dict, or None if not found
        """
        try:
            cursor = self._conn.execute(
                "SELECT * FROM runs WHERE id = ?",
                (run_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            # Update access tracking
            self._conn.execute(
                """
                UPDATE runs
                SET access_count = access_count + 1,
                    last_accessed_at = ?
                WHERE id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), run_id)
            )
            self._conn.commit()

            return dict(row)
        except Exception as e:
            print(f"[memory] error fetching run: {e}", file=sys.stderr)
            return None

    def add_note(self, content: str, source: str = "lesson", source_run_id: str | None = None) -> str:
        """Add a note (lesson or taught).

        Args:
            content: Note content
            source: "lesson" (planner-derived) or "taught" (explicit user teach: command)
            source_run_id: Optional run ID this note came from

        Returns:
            Note ID
        """
        try:
            note_id = str(uuid4())
            created_at = datetime.now(timezone.utc).isoformat()

            self._conn.execute(
                """
                INSERT INTO notes (id, content, source, source_run_id, created_at, last_accessed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (note_id, content, source, source_run_id, created_at, created_at)
            )
            self._conn.commit()
            return note_id
        except Exception as e:
            print(f"[memory] error adding note: {e}", file=sys.stderr)
            return None

    def promote(self, table: str, row_id: str) -> None:
        """Move a row up one tier (COLD→WARM→HOT).

        Args:
            table: "runs" or "notes"
            row_id: Row identifier
        """
        try:
            cursor = self._conn.execute(f"SELECT tier FROM {table} WHERE id = ?", (row_id,))
            row = cursor.fetchone()
            if not row:
                return

            current = row["tier"]
            new_tier = {"COLD": "WARM", "WARM": "HOT", "HOT": "HOT"}.get(current, "HOT")

            self._conn.execute(f"UPDATE {table} SET tier = ? WHERE id = ?", (new_tier, row_id))
            self._conn.commit()
        except Exception as e:
            print(f"[memory] error promoting row: {e}", file=sys.stderr)

    def demote(self, table: str, row_id: str) -> None:
        """Move a row down one tier (HOT→WARM→COLD).

        Args:
            table: "runs" or "notes"
            row_id: Row identifier
        """
        try:
            cursor = self._conn.execute(f"SELECT tier FROM {table} WHERE id = ?", (row_id,))
            row = cursor.fetchone()
            if not row:
                return

            current = row["tier"]
            new_tier = {"HOT": "WARM", "WARM": "COLD", "COLD": "COLD"}.get(current, "COLD")

            self._conn.execute(f"UPDATE {table} SET tier = ? WHERE id = ?", (new_tier, row_id))
            self._conn.commit()
        except Exception as e:
            print(f"[memory] error demoting row: {e}", file=sys.stderr)

    def stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dict with run/note counts and tier breakdown
        """
        try:
            stats = {}

            # Run counts
            cursor = self._conn.execute("SELECT COUNT(*) as total FROM runs")
            stats["total_runs"] = cursor.fetchone()["total"]

            cursor = self._conn.execute("SELECT tier, COUNT(*) as count FROM runs GROUP BY tier")
            stats["runs_by_tier"] = {row["tier"]: row["count"] for row in cursor}

            # Note counts
            cursor = self._conn.execute("SELECT COUNT(*) as total FROM notes")
            stats["total_notes"] = cursor.fetchone()["total"]

            cursor = self._conn.execute("SELECT tier, COUNT(*) as count FROM notes GROUP BY tier")
            stats["notes_by_tier"] = {row["tier"]: row["count"] for row in cursor}

            cursor = self._conn.execute("SELECT source, COUNT(*) as count FROM notes GROUP BY source")
            stats["notes_by_source"] = {row["source"]: row["count"] for row in cursor}

            return stats
        except Exception as e:
            print(f"[memory] error fetching stats: {e}", file=sys.stderr)
            return {}

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search runs and notes using TF-IDF similarity.

        This is a wrapper that delegates to the search module.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching documents with metadata
        """
        from .search import search
        return search(self, query, limit)

    def get_all_runs(self) -> list[dict]:
        """Fetch all runs for corpus building.

        Returns:
            List of run dicts
        """
        try:
            cursor = self._conn.execute("SELECT * FROM runs ORDER BY created_at DESC")
            return [dict(row) for row in cursor]
        except Exception as e:
            print(f"[memory] error fetching all runs: {e}", file=sys.stderr)
            return []

    def get_all_notes(self) -> list[dict]:
        """Fetch all notes for corpus building.

        Returns:
            List of note dicts
        """
        try:
            cursor = self._conn.execute("SELECT * FROM notes ORDER BY created_at DESC")
            return [dict(row) for row in cursor]
        except Exception as e:
            print(f"[memory] error fetching all notes: {e}", file=sys.stderr)
            return []

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception as e:
                print(f"[memory] error closing connection: {e}", file=sys.stderr)
