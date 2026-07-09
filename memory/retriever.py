"""MemoryRetriever - owns retrieval logic and ranking delegation."""

import sys
import time
from .ranking import rank

class MemoryRetriever:
    """Handles fetching and ranking memories."""

    def __init__(self, store: "MemoryStore"):
        """Initialize with a storage backend.

        Args:
            store: MemoryStore instance
        """
        self.store = store
        self._cache = {}
        self._cache_ttl = 60  # 60 seconds cache TTL
        
    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search memories using retrieval and ranking strategy.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching memories, ordered by relevance
        """
        try:
            cache_key = f"{query}:{limit}"
            now = time.time()

            # Check cache
            if cache_key in self._cache:
                cached_result, cached_time = self._cache[cache_key]
                if now - cached_time < self._cache_ttl:
                    return cached_result

            # 1. Obtain candidates from store (no filtering for now, fetching all)
            candidates = self.store.get_memories()

            # 2. Invoke ranking strategy
            ranked = rank(query, candidates, limit=limit)

            # Cache result
            self._cache[cache_key] = (ranked, now)

            return ranked
        except Exception as e:
            print(f"[memory] error in retriever: {e}", file=sys.stderr)
            return []
