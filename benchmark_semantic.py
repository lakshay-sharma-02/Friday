import json
import time
import os
import sqlite3
import numpy as np

# We'll use the existing memory tools
# But to test properly, we should push the corpus into the MemoryStore
# and test using MemoryRetriever.

from memory.store import MemoryStore
from memory.retriever import MemoryRetriever
from memory.ranking import rank, HybridRanker

def run_benchmark():
    print("Loading memory_benchmark.json...")
    with open("memory_benchmark.json", "r") as f:
        data = json.load(f)
        
    corpus = data["corpus"]
    scenarios = data["scenarios"]
    
    print(f"Loaded {len(corpus)} memories and {len(scenarios)} scenarios.")
    
    # 1. Initialize store and load corpus
    store = MemoryStore()
    retriever = MemoryRetriever(store)
    
    # Clean previous test memories
    store._conn.execute("DELETE FROM memories")
    store._conn.execute("DELETE FROM embedding_index")
    store._conn.commit()
    
    for mem in corpus:
        store._conn.execute(
            "INSERT INTO memories (id, type, content, importance, created_at, last_accessed, reinforcement_count, project_tag, source) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), 0, NULL, 'benchmark')",
            (mem["id"], mem["type"], mem["content"], 1.0)
        )
    store._conn.commit()
    
    print("Corpus loaded into MemoryStore.")
    
    # 2. Run benchmark
    metrics = {
        "hybrid": {"top1": 0, "top3": 0, "total": 0, "latency": []},
        "lexical": {"top1": 0, "top3": 0, "total": 0, "latency": []}
    }
    
    # Force loading of model to avoid penalizing the first request
    from memory.ranking import _ranker
    _ranker.embedding_index.backend._get_model()
    
    for scenario in scenarios:
        query = scenario["query"]
        expected = scenario["expected_top_k"]
        metrics["hybrid"]["total"] += 1
        metrics["lexical"]["total"] += 1
        
        # Test Lexical (by forcing weight 1.0 for lexical, 0.0 for semantic)
        candidates = store.get_memories()
        
        t0 = time.perf_counter()
        # Mock lexical ranker
        lexical_results = rank_lexical(query, candidates, limit=3)
        t1 = time.perf_counter()
        metrics["lexical"]["latency"].append(t1 - t0)
        
        lex_ids = [r["id"] for r in lexical_results]
        
        # Top 1
        if lex_ids and lex_ids[0] in expected:
            metrics["lexical"]["top1"] += 1
        # Top 3
        if any(eid in lex_ids for eid in expected):
            metrics["lexical"]["top3"] += 1
            
        # Test Hybrid
        t0 = time.perf_counter()
        hybrid_results = retriever.search(query, limit=3)
        t1 = time.perf_counter()
        metrics["hybrid"]["latency"].append(t1 - t0)
        
        hyb_ids = [r["id"] for r in hybrid_results]
        if hyb_ids and hyb_ids[0] in expected:
            metrics["hybrid"]["top1"] += 1
        if any(eid in hyb_ids for eid in expected):
            metrics["hybrid"]["top3"] += 1
            
    # Print Results
    for mode in ["lexical", "hybrid"]:
        total = metrics[mode]["total"]
        top1 = metrics[mode]["top1"] / total * 100
        top3 = metrics[mode]["top3"] / total * 100
        avg_lat = np.mean(metrics[mode]["latency"]) * 1000
        print(f"\n--- {mode.upper()} RETRIEVAL ---")
        print(f"Top-1 Accuracy: {top1:.1f}%")
        print(f"Top-3 Accuracy: {top3:.1f}%")
        print(f"Avg Latency:    {avg_lat:.2f} ms")
        
def rank_lexical(query: str, candidates: list[dict], limit: int = 5) -> list[dict]:
    # Pure TF-IDF Implementation for comparison
    from memory.ranking import _tokenize, _compute_tf, _compute_idf, _compute_tfidf, _cosine_similarity
    if not candidates: return []
    documents = [_tokenize(item.get("content", "")) for item in candidates]
    idf = _compute_idf(documents)
    query_tokens = _tokenize(query)
    query_tf = _compute_tf(query_tokens)
    query_tfidf = _compute_tfidf(query_tf, idf)
    results = []
    for i, tokens in enumerate(documents):
        doc_tf = _compute_tf(tokens)
        doc_tfidf = _compute_tfidf(doc_tf, idf)
        score = _cosine_similarity(query_tfidf, doc_tfidf)
        if score > 0:
            results.append({"score": score, **candidates[i]})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]

if __name__ == "__main__":
    run_benchmark()
