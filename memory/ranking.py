"""Ranking strategies for memory retrieval."""

import math
from collections import Counter
import datetime
from .embeddings import EmbeddingIndex

def _tokenize(text: str) -> list[str]:
    """Simple tokenization: lowercase, split on non-alphanumeric."""
    import re
    text = text.lower()
    tokens = re.findall(r'\b\w+\b', text)
    return tokens

def _compute_tf(tokens: list[str]) -> dict[str, float]:
    count = Counter(tokens)
    total = len(tokens)
    if total == 0:
        return {}
    return {term: freq / total for term, freq in count.items()}

def _compute_idf(corpus: list[list[str]]) -> dict[str, float]:
    num_docs = len(corpus)
    if num_docs == 0:
        return {}
    
    doc_freq = Counter()
    for tokens in corpus:
        unique_terms = set(tokens)
        for term in unique_terms:
            doc_freq[term] += 1
            
    idf = {}
    for term, df in doc_freq.items():
        idf[term] = math.log(num_docs / df)
    return idf

def _compute_tfidf(tf: dict[str, float], idf: dict[str, float]) -> dict[str, float]:
    tfidf = {}
    for term, tf_val in tf.items():
        idf_val = idf.get(term, 0)
        tfidf[term] = tf_val * idf_val
    return tfidf

def _cosine_similarity(vec1: dict[str, float], vec2: dict[str, float]) -> float:
    dot = sum(vec1.get(term, 0) * vec2.get(term, 0) for term in set(vec1) | set(vec2))
    mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)

def _vector_cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2:
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)

def _get_type_weight(mem_type: str) -> float:
    mem_type = mem_type.lower()
    if mem_type == "teaching":
        return 1.5
    elif mem_type == "lesson":
        return 1.2
    elif mem_type == "episodic":
        return 1.0
    return 1.0

def _get_recency_score(created_at: str) -> float:
    try:
        dt = datetime.datetime.fromisoformat(created_at)
        now = datetime.datetime.now(datetime.UTC)
        age_days = (now - dt).total_seconds() / (24 * 3600)
        # Decay: 1.0 for now, 0.5 for 30 days old, asymptote at 0
        return 1.0 / (1.0 + age_days / 30.0)
    except Exception:
        return 0.5

class HybridRanker:
    """Combines lexical and semantic retrieval."""
    
    def __init__(self):
        self.embedding_index = EmbeddingIndex()
        
    def rank(self, query: str, candidates: list[dict], limit: int = 5) -> list[dict]:
        if not candidates:
            return []
            
        # 1. Lexical Setup
        documents = []
        for item in candidates:
            text = item.get("content", "")
            if "intent_text" in item:
                text += " " + str(item.get("intent_text", ""))
            documents.append(_tokenize(text))
            
        idf = _compute_idf(documents)
        query_tokens = _tokenize(query)
        query_tf = _compute_tf(query_tokens)
        query_tfidf = _compute_tfidf(query_tf, idf)
        
        # 2. Semantic Setup
        # Only fetch if backend is initialized
        encoded = self.embedding_index.backend.encode([query])
        query_vector = encoded[0] if encoded else None
        
        cand_ids = [c["id"] for c in candidates if "id" in c]
        stored_embeddings = self.embedding_index.get_embeddings(cand_ids)
        
        results = []
        for i, item in enumerate(candidates):
            text = item.get("content", "")
            mem_id = item.get("id")
            
            # --- Lexical Score ---
            doc_tf = _compute_tf(documents[i])
            doc_tfidf = _compute_tfidf(doc_tf, idf)
            lexical_score = _cosine_similarity(query_tfidf, doc_tfidf)
            
            # --- Semantic Score ---
            semantic_score = 0.0
            has_embedding = False
            
            # ONLY attempt semantic if query_vector exists
            if query_vector and mem_id:
                vec = stored_embeddings.get(mem_id)
                if vec is None:
                    import threading
                    threading.Thread(
                        target=self.embedding_index.generate_and_store,
                        args=(mem_id, text),
                        daemon=True
                    ).start()
                else:
                    has_embedding = True
                    semantic_score = max(0.0, _vector_cosine_similarity(query_vector, vec))
            
            # --- Modifiers ---
            importance = float(item.get("importance", 0.0))
            recency = _get_recency_score(item.get("created_at", ""))
            type_weight = _get_type_weight(item.get("type", "episodic"))
            
            # --- Hybrid Formula ---
            # Configurable weights (hardcoded here for simplicity, but effectively parameterizable)
            if has_embedding:
                w_lex = 0.3
                w_sem = 0.7
            else:
                w_lex = 1.0
                w_sem = 0.0
            
            base_score = (w_lex * lexical_score) + (w_sem * semantic_score)
            
            final_score = base_score * type_weight
            final_score += importance * 0.1
            final_score += recency * 0.05
            
            if final_score > 0:
                results.append({
                    "score": final_score,
                    **item
                })
                
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

# Singleton ranker instance for the module
_ranker = HybridRanker()

def rank(query: str, candidates: list[dict], limit: int = 5) -> list[dict]:
    """Rank candidates using Hybrid Ranker."""
    return _ranker.rank(query, candidates, limit)
