"""
MCP retrieval tools for the Rocket Elevators RAG pipeline.

Two tools, one per ChromaDB collection:
  - search_manuals(query, k=5)   → maintenance-doc chunks
  - search_incidents(query, k=5) → incident-narrative chunks

Both collections were embedded with all-MiniLM-L6-v2 (sentence-transformers).
ChromaDB's default distance metric is squared L2 on normalised vectors, which
relates to cosine similarity as:  cosine_sim = 1 - l2_dist / 2

The returned `score` field uses that formula so 1.0 = identical, 0.0 = orthogonal.
When the best hit scores below NO_MATCH_THRESHOLD the tool returns found=False
so the chatbot can say "I don't have documentation on that" rather than hallucinate.
"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from chroma import get_client

# ── Constants ─────────────────────────────────────────────────────────────────

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

MANUALS_COLLECTION   = "manuals"
INCIDENTS_COLLECTION = "incidents"

# Squared-L2 distance above which we declare "no relevant result".
# Calibrated against real queries on the Ontario elevator dataset:
#   Good semantic match ("hydraulic pressure drops"):       dist ≈ 0.58
#   Out-of-domain ("recipe for chocolate cake"):            dist ≈ 0.95
# Threshold 0.75 sits cleanly between them (cosine_sim ≈ 0.625).
NO_MATCH_THRESHOLD = 0.75

MAX_K = 20

# ── Shared embedding function (lazy, cached) ──────────────────────────────────

_ef: SentenceTransformerEmbeddingFunction | None = None


def _get_ef() -> SentenceTransformerEmbeddingFunction:
    global _ef
    if _ef is None:
        _ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return _ef


def _get_collection(name: str) -> chromadb.Collection:
    """Get a collection, always supplying the embedding function for query embedding."""
    return get_client().get_or_create_collection(name, embedding_function=_get_ef())


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_query(query: str) -> None:
    if not isinstance(query, str):
        raise TypeError(f"query must be a string, got {type(query).__name__}")
    if not query.strip():
        raise ValueError("query must not be empty")


def _validate_k(k: int) -> None:
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError(f"k must be an integer, got {type(k).__name__}")
    if not (1 <= k <= MAX_K):
        raise ValueError(f"k must be between 1 and {MAX_K}, got {k}")


# ── Score conversion ──────────────────────────────────────────────────────────

def _dist_to_score(dist: float) -> float:
    """Convert squared-L2 distance to a [0, 1] relevance score."""
    return round(max(0.0, 1.0 - dist / 2.0), 4)


# ── Tool 1: search_manuals ────────────────────────────────────────────────────

def search_manuals(query: str, k: int = 5) -> dict:
    """
    Return the top-k maintenance-manual chunks that best match the query.

    Semantic matching: phrasing need not match the source text exactly —
    "hydraulic pressure drops" will retrieve content about "hydraulic pressure loss".

    Each hit includes full citation metadata (document_name, section, page_start)
    and a relevance score in [0, 1].  If the top score is below the no-match
    threshold the response includes found=False so the chatbot can say so
    explicitly rather than fabricate an answer.

    Args:
        query: natural-language question or keyword phrase
        k:     number of results to return (1–20, default 5)

    Raises:
        TypeError:  if query is not a string or k is not an int
        ValueError: if query is empty or k is out of range
    """
    _validate_query(query)
    _validate_k(k)

    col     = _get_collection(MANUALS_COLLECTION)
    results = col.query(
        query_texts=[query],
        n_results=min(k, col.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs      = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs or distances[0] > NO_MATCH_THRESHOLD:
        return {
            "found":   False,
            "message": (
                "No relevant maintenance documentation found for this query. "
                "The chatbot should not guess — ask the user to rephrase or "
                "consult a qualified elevator technician."
            ),
            "query":   query,
            "source":  "manuals",
        }

    hits = [
        {
            "text":          doc,
            "score":         _dist_to_score(dist),
            "document_name": meta.get("document_name"),
            "section":       meta.get("section"),
            "page_start":    meta.get("page_start"),
            "chunk_index":   meta.get("chunk_index"),
        }
        for doc, meta, dist in zip(docs, metadatas, distances)
    ]

    return {
        "found":  True,
        "count":  len(hits),
        "hits":   hits,
        "query":  query,
        "source": "manuals",
    }


# ── Tool 2: search_incidents ──────────────────────────────────────────────────

def search_incidents(query: str, k: int = 5) -> dict:
    """
    Return the top-k incident narratives that best match the query.

    Answers questions like "has flooding in an elevator shaft been reported before?"
    by finding semantically similar past incidents.

    Each hit includes citation metadata (incident_id, date, category) so the
    chatbot can refer to a specific incident record.  If the top score is below
    the no-match threshold the response includes found=False.

    Args:
        query: natural-language question or keyword phrase
        k:     number of results to return (1–20, default 5)

    Raises:
        TypeError:  if query is not a string or k is not an int
        ValueError: if query is empty or k is out of range
    """
    _validate_query(query)
    _validate_k(k)

    col     = _get_collection(INCIDENTS_COLLECTION)
    results = col.query(
        query_texts=[query],
        n_results=min(k, col.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs      = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs or distances[0] > NO_MATCH_THRESHOLD:
        return {
            "found":   False,
            "message": (
                "No relevant incident records found for this query. "
                "Either no similar incident has been recorded, or the query "
                "should be rephrased."
            ),
            "query":   query,
            "source":  "incidents",
        }

    hits = [
        {
            "text":        doc,
            "score":       _dist_to_score(dist),
            "incident_id": meta.get("incident_id"),
            "date":        meta.get("date"),
            "category":    meta.get("category"),
        }
        for doc, meta, dist in zip(docs, metadatas, distances)
    ]

    return {
        "found":  True,
        "count":  len(hits),
        "hits":   hits,
        "query":  query,
        "source": "incidents",
    }
