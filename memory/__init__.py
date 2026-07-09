"""Memory subsystem - persistent storage, retrieval, and ranking."""

from .store import MemoryStore
from .retriever import MemoryRetriever
from .importance import compute_tier, retier_all
from .manager import MemoryManager
from .ranking import _ranker
from .worker import get_worker

def initialize_memory_subsystem():
    """Eagerly initialize heavy memory dependencies (like ML models)."""
    _ranker.embedding_index.backend.initialize()
    get_worker().start()

__all__ = ["MemoryStore", "MemoryRetriever", "MemoryManager", "compute_tier", "retier_all", "initialize_memory_subsystem", "get_worker"]
