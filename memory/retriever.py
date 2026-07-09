"""MemoryRetriever - owns retrieval logic and ranking delegation."""

import sys
from .ranking import rank

class MemoryRetriever:
    """Handles fetching and ranking memories."""
    
    def __init__(self, store: "MemoryStore"):
        """Initialize with a storage backend.
        
        Args:
            store: MemoryStore instance
        """
        self.store = store
        
    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search memories using retrieval and ranking strategy.
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching memories, ordered by relevance
        """
        try:
            # 1. Obtain candidates from store (no filtering for now, fetching all)
            candidates = self.store.get_memories()
            
            # 2. Invoke ranking strategy
            ranked = rank(query, candidates, limit=limit)
            
            return ranked
        except Exception as e:
            print(f"[memory] error in retriever: {e}", file=sys.stderr)
            return []
