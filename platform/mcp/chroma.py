"""
ChromaDB client for the MCP server's RAG pipeline.

Usage:
    from chroma import get_client, get_collection

    client = get_client()
    col = get_collection("maintenance_docs")
    results = col.query(query_texts=["hydraulic pressure loss"], n_results=5)

The client is initialised lazily on first call and reused across tool invocations.
CHROMA_PATH must be set in the environment (or via .env) before calling get_client().
Defaults to rag/chroma_data/ (same default as rag/ingest.py) if not set.
"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb

_client: chromadb.PersistentClient | None = None

# Default: rag/chroma_data/ next to this file, matching ingest.py's default.
# Override with CHROMA_PATH env var (e.g. on Render).
_DEFAULT_CHROMA_PATH = str(Path(__file__).parent / "rag" / "chroma_data")


def get_client() -> chromadb.PersistentClient:
    """Return the shared ChromaDB client, creating it on first call."""
    global _client
    if _client is None:
        path = os.environ.get("CHROMA_PATH", _DEFAULT_CHROMA_PATH)
        _client = chromadb.PersistentClient(path=path)
    return _client


def get_collection(name: str) -> chromadb.Collection:
    """Return a ChromaDB collection by name, creating it if it doesn't exist."""
    return get_client().get_or_create_collection(name)
