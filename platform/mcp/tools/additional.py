"""
Additional MCP tools for Ontario elevator operations queries.

All SQL uses bound parameters. All tools include a `source` field for citation.
Date arithmetic uses Python timedelta objects passed as bound parameters so
psycopg handles the casting — no interval strings are interpolated.
"""

import datetime

from psycopg.rows import dict_row

from db import get_pool
from tools.elevators import _serialize, _validate_elevator_id


# ── Validation helpers ────────────────────────────────────────────────────────

def _validate_days(days: int) -> None:
    """Reject non-positive or unreasonably large day counts."""
    if not isinstance(days, int) or isinstance(days, bool):
        raise TypeError(f"days must be an integer, got {type(days).__name__}")
    if days <= 0:
        raise ValueError(f"days must be a positive integer, got {days}")
    if days > 3650:
        raise ValueError(f"days must be ≤ 3650 (10 years), got {days}")


# ── Tool A: expiring licences ─────────────────────────────────────────────────

def list_expiring_licences(days: int = 90) -> dict:
    """
    Return active elevators whose licence expires within the next `days` days.

    Default window is 90 days. `days` must be a positive integer ≤ 3650.
    Excludes already-inactive devices so the list contains only actionable items.
    """
    _validate_days(days)

    SQL = """
        SELECT id,
               location,
               device_type,
               license_status,
               license_expiry,
               license_holder
        FROM   elevators
        WHERE  license_status NOT IN ('INACTIVE', 'CANCELLED')
          AND  license_expiry BETWEEN CURRENT_DATE
                                  AND CURRENT_DATE + %s
        ORDER  BY license_expiry ASC
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL, (datetime.timedelta(days=days),))
            rows = [_serialize(dict(r)) for r in cur.fetchall()]
    return {
        "days_window": days,
        "count":       len(rows),
        "rows":        rows,
        "source":      "elevators",
    }


# ── Tool B: overdue inspections ───────────────────────────────────────────────

def list_overdue_inspections(days: int = 365, limit: int = 100) -> dict:
    """
    Return active elevators that have not had an inspection in more than `days`
    days, or have never been inspected.

    `days` must be a positive integer ≤ 3650. `limit` caps results (default 100,
    max 500) to avoid overwhelming the chatbot context.

    Ordered by last inspection date ascending (never-inspected first).
    """
    _validate_days(days)
    if not isinstance(limit, int) or isinstance(limit, bool) or not (1 <= limit <= 500):
        raise ValueError(f"limit must be an integer between 1 and 500, got {limit!r}")

    SQL = """
        WITH latest AS (
            SELECT DISTINCT ON (elevator_id)
                   elevator_id,
                   latest_date
            FROM   inspections
            ORDER  BY elevator_id, latest_date DESC NULLS LAST
        )
        SELECT e.id,
               e.location,
               e.device_type,
               e.license_status,
               l.latest_date                       AS last_inspection_date,
               (CURRENT_DATE - l.latest_date)      AS days_since_inspection
        FROM   elevators e
        LEFT   JOIN latest l ON l.elevator_id = e.id
        WHERE  e.license_status = 'ACTIVE'
          AND  (l.latest_date IS NULL
                OR l.latest_date < CURRENT_DATE - %s)
        ORDER  BY l.latest_date ASC NULLS FIRST
        LIMIT  %s
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL, (datetime.timedelta(days=days), limit))
            rows = [_serialize(dict(r)) for r in cur.fetchall()]
    return {
        "days_threshold": days,
        "limit":          limit,
        "count":          len(rows),
        "rows":           rows,
        "source":         "elevators, inspections",
    }


# ── Tool C: incident root-cause summary ──────────────────────────────────────

def get_incident_root_cause_summary() -> dict:
    """
    Return a fleet-wide breakdown of incident root causes, ordered by frequency.

    Null root_cause values (recorded as unknown) are grouped under
    'Unknown / Not recorded'. Includes the percentage each cause represents
    of all incidents so comparisons are immediately readable.
    """
    SQL = """
        SELECT COALESCE(root_cause, 'Unknown / Not recorded') AS root_cause,
               COUNT(*)                                        AS count,
               ROUND(
                   COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
                   1
               )                                              AS percentage
        FROM   incidents
        GROUP  BY root_cause
        ORDER  BY count DESC
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]
    total = sum(r["count"] for r in rows)
    # cast Decimal to float for JSON serialisation
    for r in rows:
        r["count"]      = int(r["count"])
        r["percentage"] = float(r["percentage"])
    return {
        "total_incidents": total,
        "breakdown":       rows,
        "source":          "incidents",
    }


# ── Tool D: alterations pending follow-up ────────────────────────────────────

def list_alterations_pending_followup() -> dict:
    """
    Return all alteration requests currently in 'Pending Follow Up' status.

    These are alterations where work has been registered but a follow-up
    inspection has not yet been completed. Operations teams need this list
    to track open alteration work and ensure follow-up inspections are scheduled.
    """
    SQL = """
        SELECT a.id,
               a.elevator_id,
               e.location,
               e.device_type,
               a.alteration_type,
               a.summary,
               a.status,
               a.customer
        FROM   alterations a
        JOIN   elevators   e ON e.id = a.elevator_id
        WHERE  a.status = 'Pending Follow Up'
        ORDER  BY a.elevator_id, a.id
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL)
            rows = [_serialize(dict(r)) for r in cur.fetchall()]
    return {
        "count":  len(rows),
        "rows":   rows,
        "source": "alterations, elevators",
    }
