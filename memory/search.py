"""Deterministic TF-IDF search over runs and notes."""

import sys
import math
from collections import Counter
from typing import Any


def _tokenize(text: str) -> list[str]:
    """Simple tokenization: lowercase, split on non-alphanumeric."""
    import re
    text = text.lower()
    tokens = re.findall(r'\b\w+\b', text)
    return tokens


def _compute_tf(tokens: list[str]) -> dict[str, float]:
    """Compute term frequency for a document.

    Args:
        tokens: List of tokens

    Returns:
        Dict mapping term to frequency
    """
    count = Counter(tokens)
    total = len(tokens)
    if total == 0:
        return {}
    return {term: freq / total for term, freq in count.items()}


def _compute_idf(corpus: list[list[str]]) -> dict[str, float]:
    """Compute inverse document frequency across corpus.

    Args:
        corpus: List of token lists (one per document)

    Returns:
        Dict mapping term to IDF score
    """
    num_docs = len(corpus)
    if num_docs == 0:
        return {}

    # Count documents containing each term
    doc_freq = Counter()
    for tokens in corpus:
        unique_terms = set(tokens)
        for term in unique_terms:
            doc_freq[term] += 1

    # Compute IDF: log(N / df)
    idf = {}
    for term, df in doc_freq.items():
        idf[term] = math.log(num_docs / df)

    return idf


def _compute_tfidf(tf: dict[str, float], idf: dict[str, float]) -> dict[str, float]:
    """Compute TF-IDF scores.

    Args:
        tf: Term frequency dict
        idf: Inverse document frequency dict

    Returns:
        Dict mapping term to TF-IDF score
    """
    tfidf = {}
    for term, tf_val in tf.items():
        idf_val = idf.get(term, 0)
        tfidf[term] = tf_val * idf_val
    return tfidf


def _cosine_similarity(vec1: dict[str, float], vec2: dict[str, float]) -> float:
    """Compute cosine similarity between two TF-IDF vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Similarity score (0-1)
    """
    # Compute dot product
    dot = sum(vec1.get(term, 0) * vec2.get(term, 0) for term in set(vec1) | set(vec2))

    # Compute magnitudes
    mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot / (mag1 * mag2)


def search(store: "MemoryStore", query: str, limit: int = 5) -> list[dict]:
    """Search runs and notes using TF-IDF similarity.

    Implementation: from-scratch TF-IDF using stdlib (no dependencies).
    Rationale: Zero new dependencies, simple to audit, fast enough for
    a few thousand documents. sklearn would be faster but adds a heavy
    dependency for a single use case.

    Args:
        store: MemoryStore instance
        query: Search query
        limit: Maximum results to return

    Returns:
        List of matching documents with metadata, sorted by relevance
    """
    try:
        # Build corpus
        runs = store.get_all_runs()
        notes = store.get_all_notes()

        documents = []
        metadata = []

        for run in runs:
            text = run.get("intent_text", "")
            tokens = _tokenize(text)
            documents.append(tokens)
            metadata.append({
                "source": "runs",
                "id": run["id"],
                "text": text,
                "status": run.get("status"),
                "created_at": run.get("created_at"),
            })

        for note in notes:
            text = note.get("content", "")
            tokens = _tokenize(text)
            documents.append(tokens)
            metadata.append({
                "source": "notes",
                "id": note["id"],
                "text": text,
                "note_source": note.get("source"),
                "created_at": note.get("created_at"),
            })

        if not documents:
            return []

        # Compute IDF across corpus
        idf = _compute_idf(documents)

        # Compute TF-IDF for query
        query_tokens = _tokenize(query)
        query_tf = _compute_tf(query_tokens)
        query_tfidf = _compute_tfidf(query_tf, idf)

        # Compute TF-IDF for each document and similarity to query
        results = []
        for i, tokens in enumerate(documents):
            doc_tf = _compute_tf(tokens)
            doc_tfidf = _compute_tfidf(doc_tf, idf)
            score = _cosine_similarity(query_tfidf, doc_tfidf)

            if score > 0:
                results.append({
                    "score": score,
                    **metadata[i]
                })

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:limit]

    except Exception as e:
        print(f"[memory] error searching: {e}", file=sys.stderr)
        return []
