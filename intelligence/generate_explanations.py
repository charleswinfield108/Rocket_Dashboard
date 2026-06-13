#!/usr/bin/env python3
# AND-105 Task 7: Batch Risk Explanation Generation
#
# Connects to PostgreSQL, queries the top 500 elevators by risk_score,
# generates a natural-language risk explanation for each via the local
# Ollama API, and stores the result in predictions.risk_explanation.
#
# Idempotent: re-running overwrites existing explanations without error.
# Resilient: retries once on timeout; logs and skips on repeated failure.
# Checkpointed: commits every 50 rows so partial runs survive interruption.

import os
import sys
import time
import logging
from datetime import date, timedelta

import psycopg2
import psycopg2.extras
import requests

# ── Configuration ──────────────────────────────────────────────────────────────
DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "rocketdash"),
    user=os.getenv("DB_USER", "rocketdash"),
    password=os.getenv("DB_PASSWORD", "changeme"),
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))  # seconds per call
TWO_YEARS_AGO = (date.today() - timedelta(days=730)).isoformat()

# ── System prompt (V3-final from Task 6, Reviewer-corrected) ──────────────────
# Changes vs V3: removed "TSSA" hallucination anchor (R1), softened sentence
# count for sparse data (R2), caller substitutes "(date unknown)" for NULLs (R3).
SYSTEM_PROMPT = """You are an elevator safety analyst for a regulated fleet writing risk \
summaries for operations managers.

The risk score is the model's predicted probability (0–1) that the next inspection will result \
in a "Follow up" outcome — meaning unresolved safety orders will remain open after inspection. \
A score above 0.8 is classified high risk.

Write 1-3 sentences. Use fewer sentences if the data is sparse. Rules:
1. Cite specific values from the data: dates, outcome strings, counts, or incident categories.
   Example: "The last three inspections (2016-04-13, 2015-11-02, 2015-04-27) all resulted in Follow up."
2. If a data field is empty or absent, write "no [field] on record" — do not infer or fill in.
3. Do not use hedging language (no "may", "might", "could").
4. Do not repeat the risk level or risk score in your explanation.
5. Do not add bullet points, headers, or lists."""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── DB helpers ─────────────────────────────────────────────────────────────────

def gather_context(cur, elevator_id: int) -> dict:
    """Return inspections, incidents (past 2 yr), and alterations for one elevator."""
    cur.execute("""
        SELECT
            TO_CHAR(latest_date, 'YYYY-MM-DD') AS date,
            COALESCE(inspection_type, 'unknown') AS type,
            COALESCE(outcome, 'unknown') AS outcome
        FROM inspections
        WHERE elevator_id = %s
        ORDER BY latest_date DESC NULLS LAST
        LIMIT 5
    """, (elevator_id,))
    inspections = [dict(r) for r in cur.fetchall()]

    cur.execute("""
        SELECT
            TO_CHAR(date_of_occurrence, 'YYYY-MM-DD') AS date,
            COALESCE(category, 'unknown') AS category,
            COALESCE(incident_summary, '') AS summary
        FROM incidents
        WHERE elevator_id = %s
          AND date_of_occurrence >= %s::date
        ORDER BY date_of_occurrence DESC
    """, (elevator_id, TWO_YEARS_AGO))
    incidents = [dict(r) for r in cur.fetchall()]

    cur.execute("""
        SELECT
            COALESCE(alteration_type, 'unknown') AS type,
            COALESCE(status, 'unknown') AS status,
            COALESCE(summary, '') AS summary
        FROM alterations
        WHERE elevator_id = %s
        ORDER BY id DESC
        LIMIT 10
    """, (elevator_id,))
    alterations = [dict(r) for r in cur.fetchall()]

    return {"inspections": inspections, "incidents": incidents, "alterations": alterations}


def build_user_message(elev: dict, ctx: dict) -> str:
    """Build the structured user message with None-date substitution."""
    def safe_date(d: str | None) -> str:
        return d if d and d != "None" else "(date unknown)"

    insp_lines = "\n".join(
        f"  - {safe_date(i['date'])}: {i['type']} → {i['outcome']}"
        for i in ctx["inspections"]
    ) or "  (no inspections on record)"

    incident_lines = "\n".join(
        f"  - {safe_date(i['date'])}: {i['category']} — {i['summary'][:80]}"
        for i in ctx["incidents"]
    ) or "  (no incidents in past 2 years)"

    alt_lines = "\n".join(
        f"  - {a['type']}: {a['status']} — {a['summary'][:60]}"
        for a in ctx["alterations"]
    ) or "  (no alterations on record)"

    return (
        f"Elevator ID: {elev['elevator_id']}\n"
        f"Location: {elev['location']}\n"
        f"Equipment type: {elev['device_type']}\n"
        f"Device status: {elev['device_status']}\n"
        f"License status: {elev['license_status']}\n"
        f"Risk level: {elev['risk_level']}\n"
        f"Predicted outcome: {elev['predicted_outcome']} (confidence {elev['confidence']:.1%})\n"
        f"\nLast 5 inspections (most recent first):\n{insp_lines}"
        f"\n\nIncidents in past 2 years:\n{incident_lines}"
        f"\n\nRecent alterations:\n{alt_lines}"
        f"\n\nWrite the risk explanation now."
    )


# ── Ollama helper ──────────────────────────────────────────────────────────────

def call_ollama(user_message: str) -> str:
    """
    POST to Ollama /api/chat. Raises requests.exceptions.Timeout on timeout.
    All other HTTP errors raise requests.exceptions.HTTPError.
    """
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    resp = requests.post(
        f"{OLLAMA_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def generate_with_retry(user_message: str, elevator_id: int) -> str | None:
    """
    Call Ollama with one retry on Timeout. Returns the explanation string,
    or None if both attempts fail. Logs all failures.
    """
    for attempt in range(1, 3):
        try:
            return call_ollama(user_message)
        except requests.exceptions.Timeout:
            if attempt == 1:
                log.warning("Elevator %d: timeout on attempt 1, retrying…", elevator_id)
            else:
                log.error("Elevator %d: timeout on attempt 2, skipping.", elevator_id)
        except requests.exceptions.HTTPError as e:
            log.error("Elevator %d: HTTP error %s, skipping.", elevator_id, e)
            return None
        except Exception as e:
            log.error("Elevator %d: unexpected error %s, skipping.", elevator_id, e)
            return None
    return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    # ── Connect to DB ──────────────────────────────────────────────────────────
    conn = psycopg2.connect(**DB)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    log.info("DB connected: %s", conn.get_dsn_parameters()["dbname"])

    # ── Verify Ollama ──────────────────────────────────────────────────────────
    try:
        tags_resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        tags_resp.raise_for_status()
    except Exception as e:
        log.error("Cannot reach Ollama at %s: %s", OLLAMA_URL, e)
        sys.exit(1)

    available = [m["name"] for m in tags_resp.json().get("models", [])]
    if MODEL not in available:
        log.error("Model %s not found. Available: %s", MODEL, available)
        sys.exit(1)
    log.info("Ollama ready — model: %s", MODEL)

    # ── Query top N elevators by risk_score ────────────────────────────────────
    cur.execute("""
        SELECT
            p.elevator_id,
            p.risk_score::float,
            p.risk_level,
            p.predicted_outcome,
            p.confidence::float,
            COALESCE(e.location,      'unknown') AS location,
            COALESCE(e.device_type,   'unknown') AS device_type,
            COALESCE(e.device_status, 'unknown') AS device_status,
            COALESCE(e.license_status,'unknown') AS license_status
        FROM predictions p
        JOIN elevators e ON e.id = p.elevator_id
        ORDER BY p.risk_score DESC
        LIMIT %s
    """, (BATCH_SIZE,))
    elevators = cur.fetchall()
    total = len(elevators)
    log.info("Fetched %d elevators (top %d by risk_score)", total, BATCH_SIZE)

    # ── Generate and store ─────────────────────────────────────────────────────
    total_start = time.monotonic()
    generated = 0
    failures = 0

    for i, elev in enumerate(elevators, start=1):
        eid = elev["elevator_id"]
        print(
            f"Processing elevator {i}/{total}  "
            f"(ID={eid}, score={elev['risk_score']:.4f}, {elev['risk_level']})…",
            flush=True,
        )

        t0 = time.monotonic()
        ctx = gather_context(cur, eid)
        msg = build_user_message(dict(elev), ctx)
        explanation = generate_with_retry(msg, eid)
        elapsed = time.monotonic() - t0

        if explanation is not None:
            cur.execute(
                "UPDATE predictions SET risk_explanation = %s WHERE elevator_id = %s",
                (explanation, eid),
            )
            generated += 1
            print(f"  ✓ {elapsed:.1f}s  {explanation[:72]}…")
        else:
            failures += 1
            print(f"  ✗ failed after {elapsed:.1f}s")

        # Commit checkpoint every 50 rows — preserves progress on interruption
        if i % 50 == 0:
            conn.commit()
            log.info("Checkpoint commit at %d/%d", i, total)

    conn.commit()

    # ── Verification query ─────────────────────────────────────────────────────
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE risk_explanation IS NOT NULL)     AS with_explanation,
            COUNT(*) FILTER (WHERE risk_explanation IS NULL)         AS without_explanation,
            AVG(LENGTH(risk_explanation))
                FILTER (WHERE risk_explanation IS NOT NULL)          AS avg_length
        FROM (
            SELECT elevator_id, risk_explanation
            FROM predictions
            ORDER BY risk_score DESC
            LIMIT %s
        ) sub
    """, (BATCH_SIZE,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    total_elapsed = time.monotonic() - total_start
    print()
    print("=" * 60)
    print("SUMMARY")
    print(f"  Elevators queried:          {total}")
    print(f"  Explanations generated:     {generated}")
    print(f"  Failures (skipped):         {failures}")
    print(f"  DB rows with explanation:   {row['with_explanation']}")
    print(f"  DB rows still NULL:         {row['without_explanation']}")
    print(f"  Average explanation length: {row['avg_length']:.0f} chars" if row['avg_length'] else
          "  Average explanation length: n/a")
    print(f"  Total elapsed time:         {total_elapsed / 60:.1f} min")
    print("=" * 60)

    if row['without_explanation'] > 0:
        log.warning(
            "%d rows still NULL after processing — re-run to retry failures.",
            row['without_explanation'],
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
