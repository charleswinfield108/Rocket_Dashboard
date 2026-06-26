# RAG Ingestion Pipeline

Loads two knowledge sources into ChromaDB for use by the Rocket Elevators MCP server.

## Quick start

```bash
cd platform/mcp/rag

# First run — ingest everything
python3 ingest.py \
  --db-url postgresql://user:pass@host:5432/dbname \
  --chroma-path ./chroma_data

# Rebuild from scratch (drops both collections first)
python3 ingest.py --db-url ... --reset

# Custom PDF directory
python3 ingest.py --docs-dir /path/to/pdfs --db-url ...
```

`DATABASE_URL` and `CHROMA_PATH` can be set in a `.env` file instead of passed as flags.

## Collection design — two collections

The pipeline uses **two separate ChromaDB collections** rather than one with a `source_type` filter:

| Collection   | Content                          | Chunk strategy                   |
|-------------|----------------------------------|----------------------------------|
| `manuals`    | 6 maintenance PDFs               | One chunk per section (≤ 300 words); large sections split with 40-word overlap |
| `incidents`  | ~2,444 incident narratives       | One chunk per incident           |

**Why two collections?** Different retrieval needs call for different query strategies. A question like *"how do I adjust the brake?"* should only search manuals. A question like *"what incidents involved flooding?"* should only search incidents. Keeping them separate lets the retrieval tool target the right collection without filtering noise, and keeps embedding space unpolluted by mixing procedural text with short incident narratives.

## Embedding model

**`all-MiniLM-L6-v2`** (sentence-transformers, via ChromaDB's `SentenceTransformerEmbeddingFunction`)

- 384-dimensional dense vectors
- ~22M parameters — fast on CPU, no GPU required
- Downloaded once from HuggingFace Hub (~90 MB); cached locally after first run
- Consistently top-ranked on the SBERT benchmarks for short-to-medium text retrieval

## Chunk metadata

Every chunk carries metadata for downstream citation:

**Manuals:**
```json
{
  "source_type":   "manual",
  "document_name": "hydraulic_maintenance",
  "section":       "Control Valve - Adjustment and Testing",
  "page_start":    3,
  "chunk_index":   4
}
```

**Incidents:**
```json
{
  "source_type": "incident",
  "incident_id": 518574,
  "date":        "2011-01-06",
  "category":    "ED-Near Miss"
}
```

## Idempotency

Without `--reset`, the pipeline calls `collection.upsert()` with stable deterministic IDs
(`manual_<slug>_<offset>` and `incident_<offset>`). Re-running updates chunks in place
and never creates duplicates.

`--reset` deletes both collections and rebuilds from scratch — use this when PDFs change
or the embedding model is upgraded.

## PDF chunking strategy

PDFs were authored with `## Heading` prefixes on section titles (see `_create_sample_pdfs.py`).
The chunker (`_chunk_pdf.py`) splits on these headings, keeping each section as one chunk.
Sections exceeding 300 words are split into overlapping sub-chunks (40-word overlap) so no
single retrieval result is too long for the LLM context.

## Files

```
rag/
├── ingest.py               # main entry point
├── _chunk_pdf.py           # PDF section-based chunking
├── _chunk_incidents.py     # incident narrative chunking (PostgreSQL)
├── _create_sample_pdfs.py  # generates the 6 reference PDFs (run once)
├── docs/                   # maintenance PDF knowledge base
│   ├── hydraulic_maintenance.pdf
│   ├── traction_troubleshooting.pdf
│   ├── safety_code_quick_reference.pdf
│   ├── inspection_types.pdf
│   ├── common_failure_modes.pdf
│   └── emergency_response.pdf
└── chroma_data/            # ChromaDB on-disk store (git-ignored)
```
