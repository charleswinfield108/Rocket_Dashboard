"""
RAG ingestion pipeline for Rocket Elevators MCP.

Loads two knowledge sources into ChromaDB:
  - Maintenance PDFs (collection: "manuals")
  - Incident narratives from PostgreSQL (collection: "incidents")

Usage:
    python3 ingest.py                            # ingest from default paths
    python3 ingest.py --docs-dir /path/to/pdfs  # custom PDF directory
    python3 ingest.py --reset                    # drop and rebuild both collections
    python3 ingest.py --db-url postgresql://...  # override DB URL

Environment variables (all optional if defaults suffice):
    CHROMA_PATH   path for the ChromaDB on-disk store (default: ./chroma_data)
    DATABASE_URL  PostgreSQL connection string

The script is idempotent by default: documents are upserted by ID so
re-running without --reset updates existing chunks rather than duplicating them.
"""

import argparse
import os
import sys
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv

from _chunk_pdf      import chunk_pdf
from _chunk_incidents import chunk_incidents

load_dotenv()

# ── Embedding function ────────────────────────────────────────────────────────
# all-MiniLM-L6-v2: 384-dimensional, ~22M params, fast CPU inference.
# Good balance of quality and speed for short-to-medium text chunks.
# Downloaded once from HuggingFace Hub on first run (~90 MB).
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── Collection names ──────────────────────────────────────────────────────────
# Two separate collections keep retrieval scopes clean:
#   - "manuals"   for PDF maintenance documents
#   - "incidents" for free-text incident narratives
# The retrieval tool can query one or both depending on the question type.
MANUALS_COLLECTION   = "manuals"
INCIDENTS_COLLECTION = "incidents"

# Batch size for ChromaDB upserts
UPSERT_BATCH = 500


def _get_db_url(override: str | None) -> str:
    url = override or os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit(
            "ERROR: No database URL. Set DATABASE_URL in .env or pass --db-url."
        )
    return url


def _get_chroma_path(override: str | None) -> str:
    return override or os.environ.get("CHROMA_PATH", str(Path(__file__).parent / "chroma_data"))


def _make_ef() -> SentenceTransformerEmbeddingFunction:
    print(f"Loading embedding model '{EMBEDDING_MODEL}' ...")
    return SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


def _get_or_reset_collection(
    client: chromadb.PersistentClient,
    name: str,
    ef: SentenceTransformerEmbeddingFunction,
    reset: bool,
) -> chromadb.Collection:
    if reset:
        try:
            client.delete_collection(name)
            print(f"  Deleted existing collection '{name}'")
        except Exception:
            pass
    return client.get_or_create_collection(name, embedding_function=ef)


def _upsert_chunks(
    collection: chromadb.Collection,
    chunks: list[dict],
    id_prefix: str,
) -> int:
    """Upsert chunks in batches. Returns number of chunks upserted."""
    total = 0
    for start in range(0, len(chunks), UPSERT_BATCH):
        batch = chunks[start : start + UPSERT_BATCH]
        ids        = [f"{id_prefix}_{start + i}" for i in range(len(batch))]
        documents  = [c["text"]     for c in batch]
        metadatas  = [c["metadata"] for c in batch]
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        total += len(batch)
    return total


def ingest_manuals(
    collection: chromadb.Collection,
    docs_dir: Path,
) -> dict[str, int]:
    """Chunk and upsert all PDFs found in docs_dir. Returns {filename: chunk_count}."""
    pdf_files = sorted(docs_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"  WARNING: No PDFs found in {docs_dir}")
        return {}

    summary: dict[str, int] = {}
    for pdf_path in pdf_files:
        chunks = chunk_pdf(pdf_path)
        slug   = pdf_path.stem.replace(" ", "_").lower()
        upserted = _upsert_chunks(collection, chunks, id_prefix=f"manual_{slug}")
        summary[pdf_path.name] = upserted
        print(f"    {pdf_path.name}: {upserted} chunks")
    return summary


def ingest_incidents(
    collection: chromadb.Collection,
    db_url: str,
) -> int:
    """Chunk and upsert all incident narratives. Returns chunk count."""
    print("  Fetching incident narratives from PostgreSQL ...")
    chunks = chunk_incidents(db_url)
    print(f"  {len(chunks)} narratives fetched - upserting ...")
    upserted = _upsert_chunks(collection, chunks, id_prefix="incident")
    return upserted


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest knowledge sources into ChromaDB")
    parser.add_argument(
        "--docs-dir",
        default=str(Path(__file__).parent / "docs"),
        help="Directory containing maintenance PDFs (default: rag/docs/)",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="PostgreSQL connection string (overrides DATABASE_URL env var)",
    )
    parser.add_argument(
        "--chroma-path",
        default=None,
        help="Path for the ChromaDB on-disk store (overrides CHROMA_PATH env var)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and rebuild both collections from scratch",
    )
    args = parser.parse_args(argv)

    db_url      = _get_db_url(args.db_url)
    chroma_path = _get_chroma_path(args.chroma_path)
    docs_dir    = Path(args.docs_dir)

    if not docs_dir.is_dir():
        sys.exit(f"ERROR: docs directory not found: {docs_dir}")

    print(f"\nChromaDB path : {chroma_path}")
    print(f"Docs directory: {docs_dir}")
    print(f"Reset mode    : {args.reset}\n")

    ef     = _make_ef()
    client = chromadb.PersistentClient(path=chroma_path)

    # ── Manuals ──
    print("==> Ingesting maintenance PDFs ...")
    manuals_col  = _get_or_reset_collection(client, MANUALS_COLLECTION, ef, args.reset)
    manual_stats = ingest_manuals(manuals_col, docs_dir)
    manual_total = sum(manual_stats.values())

    # ── Incidents ──
    print("\n==> Ingesting incident narratives ...")
    incidents_col   = _get_or_reset_collection(client, INCIDENTS_COLLECTION, ef, args.reset)
    incidents_total = ingest_incidents(incidents_col, db_url)

    # ── Summary ──
    print("\n" + "=" * 50)
    print("INGESTION SUMMARY")
    print("=" * 50)
    print(f"\nManuals collection ('{MANUALS_COLLECTION}'):")
    for name, count in manual_stats.items():
        print(f"  {name:<45} {count:>4} chunks")
    print(f"  {'TOTAL':<45} {manual_total:>4} chunks")

    print(f"\nIncidents collection ('{INCIDENTS_COLLECTION}'):")
    print(f"  {'incident narratives':<45} {incidents_total:>4} chunks")

    grand_total = manual_total + incidents_total
    print(f"\n  Grand total embedded: {grand_total} chunks")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
