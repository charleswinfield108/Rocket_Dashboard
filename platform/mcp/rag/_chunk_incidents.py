"""
Incident narrative chunking for the RAG ingestion pipeline.

Each non-empty incident narrative becomes one chunk. Narratives in the
Ontario dataset average 15-30 words -- no sub-chunking is needed.

Chunk format:
    Incident #<id> (<date>)
    Category: <category>
    Summary: <incident_summary>
    <narrative>

Metadata per chunk:
    source_type:  "incident"
    incident_id:  int
    date:         ISO date string or ""
    category:     str
"""

import datetime

import psycopg
from psycopg.rows import dict_row


_SQL = """
    SELECT id,
           category,
           incident_summary,
           date_of_occurrence,
           narrative
    FROM   incidents
    WHERE  narrative IS NOT NULL
      AND  LENGTH(TRIM(narrative)) > 0
    ORDER  BY id
"""


def chunk_incidents(db_url: str) -> list[dict]:
    """
    Connect to PostgreSQL at db_url and return one chunk per incident narrative.
    """
    chunks: list[dict] = []

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(_SQL)
            rows = cur.fetchall()

    for row in rows:
        date_val = row["date_of_occurrence"]
        if isinstance(date_val, (datetime.date, datetime.datetime)):
            date_str = date_val.isoformat()
        else:
            date_str = str(date_val) if date_val else ""

        header = (
            f"Incident #{row['id']} ({date_str})\n"
            f"Category: {row['category'] or 'N/A'}\n"
            f"Summary: {row['incident_summary'] or 'N/A'}"
        )
        text = f"{header}\n{row['narrative'].strip()}"

        chunks.append({
            "text": text,
            "metadata": {
                "source_type": "incident",
                "incident_id": row["id"],
                "date":        date_str,
                "category":    row["category"] or "",
            },
        })

    return chunks
