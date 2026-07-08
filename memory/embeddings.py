"""Semantic embeddings generation and index management for Memory."""

import sqlite3
import sys
import datetime
import numpy as np

class EmbeddingBackend:
    """Isolates the actual embedding model to make it swappable."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.version = "v1.0"
        self._model = None
        self._initialized = False
        self._available = False
        
    def initialize(self):
        if self._initialized:
            return self._available

        from core.output_mode import log_debug
        log_debug("Loading embedding backend...")
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._available = True
            log_debug("Embedding backend ready.")
        except Exception:
            print("Embedding backend unavailable. Using lexical retrieval.", file=sys.stderr)
            self._model = None
            self._available = False

        self._initialized = True
        return self._available
        
    def encode(self, texts: list[str]) -> list[list[float]] | None:
        if not self._available or not self._model:
            return None
        try:
            embeddings = self._model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            print(f"[embeddings] Warning: Encoding failed ({e}).", file=sys.stderr)
            return None

class EmbeddingIndex:
    """Manages the embedding_index table independently of MemoryStore."""
    
    def __init__(self, db_path: str = ".friday_memory.db", backend: EmbeddingBackend = None):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.backend = backend or EmbeddingBackend()
        
    def _serialize(self, vector: list[float]) -> bytes:
        return np.array(vector, dtype=np.float32).tobytes()
        
    def _deserialize(self, data: bytes) -> list[float]:
        return np.frombuffer(data, dtype=np.float32).tolist()

    def generate_and_store(self, memory_id: str, content: str):
        """Generate and store embedding for a memory."""
        vectors = self.backend.encode([content])
        if not vectors:
            return
            
        vector = vectors[0]
        blob = self._serialize(vector)
        
        now = datetime.datetime.utcnow().isoformat()
        
        try:
            # Upsert
            self._conn.execute("""
                INSERT INTO embedding_index (id, memory_id, embedding_model, embedding_version, embedding_vector, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    embedding_vector = excluded.embedding_vector,
                    embedding_model = excluded.embedding_model,
                    embedding_version = excluded.embedding_version,
                    created_at = excluded.created_at
            """, (f"emb_{memory_id}", memory_id, self.backend.model_name, self.backend.version, blob, now))
            self._conn.commit()
        except Exception as e:
            print(f"[embeddings] Failed to store embedding for {memory_id}: {e}", file=sys.stderr)

    def delete_embedding(self, memory_id: str):
        """Delete embedding for a memory."""
        try:
            self._conn.execute("DELETE FROM embedding_index WHERE memory_id = ?", (memory_id,))
            self._conn.commit()
        except Exception as e:
            print(f"[embeddings] Failed to delete embedding for {memory_id}: {e}", file=sys.stderr)
            
    def get_embedding(self, memory_id: str) -> list[float] | None:
        """Retrieve embedding vector for a memory."""
        try:
            cursor = self._conn.execute(
                "SELECT embedding_vector FROM embedding_index WHERE memory_id = ?", (memory_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._deserialize(row["embedding_vector"])
        except Exception as e:
            print(f"[embeddings] Failed to get embedding for {memory_id}: {e}", file=sys.stderr)
        return None
        
    def get_embeddings(self, memory_ids: list[str]) -> dict[str, list[float]]:
        """Retrieve embeddings for multiple memories."""
        if not memory_ids:
            return {}
            
        result = {}
        placeholders = ",".join("?" * len(memory_ids))
        try:
            cursor = self._conn.execute(
                f"SELECT memory_id, embedding_vector FROM embedding_index WHERE memory_id IN ({placeholders})",
                memory_ids
            )
            for row in cursor.fetchall():
                result[row["memory_id"]] = self._deserialize(row["embedding_vector"])
        except Exception as e:
            print(f"[embeddings] Failed to get embeddings: {e}", file=sys.stderr)
        return result

    def rebuild_index(self, memories_generator):
        """Rebuild embeddings for all given memories."""
        # memories_generator is an iterable of dicts with 'id' and 'content'
        for mem in memories_generator:
            self.generate_and_store(mem["id"], mem.get("content", ""))
