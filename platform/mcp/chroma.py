"""
ChromaDB client for the MCP server's RAG pipeline.

Usage:
    from chroma import get_client, get_collection

    client = get_client()
    col = get_collection("maintenance_docs")
    results = col.query(query_texts=["hydraulic pressure loss"], n_results=5)

The client is initialised lazily on first call and reused across tool invocations.
CHROMA_PATH must be set in the environment (or via .env) before calling get_client().
It defaults to ./chroma_data if not set.
"""

import os
import chromadb
from chromadb import PersistentClient

_client: PersistentClient | None = None


def get_client() -> PersistentClient:
    """Return the shared ChromaDB client, creating it on first call."""
    global _client
    if _client is None:
        path = os.environ.get("CHROMA_PATH", "./chroma_data")
        _client = chromadb.PersistentClient(path=path)
    return _client


def get_collection(name: str) -> chromadb.Collection:
    """Return a ChromaDB collection by name, creating it if it doesn't exist."""
    return get_client().get_or_create_collection(name)
