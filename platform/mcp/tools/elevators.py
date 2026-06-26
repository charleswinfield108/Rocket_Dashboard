"""
MCP tools for the five required elevator data queries.

All SQL uses bound parameters — never string interpolation.
All tools return a `source` field naming the table(s) used so the chatbot
can cite them in responses (e.g. "Source: elevators table").
"""

import datetime

from psycopg.rows import dict_row

from db import get_pool


# ── Validation helpers ────────────────────────────────────────────────────────

_CURRENT_YEAR = datetime.date.today().year


def _validate_elevator_id(elevator_id: int) -> None:
    """Reject non-positive IDs before they touch the DB."""
    if not isinstance(elevator_id, int) or isinstance(elevator_id, bool):
        raise TypeError(f"elevator_id must be an integer, got {type(elevator_id).__name__}")
    if elevator_id <= 0:
        raise ValueError(f"elevator_id must be a positive integer, got {elevator_id}")


def _validate_year(year: int) -> None:
    """Reject years outside the plausible range of the dataset."""
    if not isinstance(year, int) or isinstance(year, bool):
        raise TypeError(f"year must be an integer, got {type(year).__name__}")
    if not (1990 <= year <= _CURRENT_YEAR):
        raise ValueError(
            f"year must be between 1990 and {_CURRENT_YEAR}, got {year}"
        )


def _serialize(row: dict) -> dict:
    """Convert date/time values to ISO strings for JSON-safe output."""
    return {
        k: v.isoformat() if isinstance(v, (datetime.date, datetime.time)) else v
        for k, v in row.items()
    }


# ── Tool 1 ────────────────────────────────────────────────────────────────────

def list_tssa_shutdown_elevators() -> dict:
    """
    Return all elevators currently flagged as shut down by TSSA.
    Filters elevators where device_status = 'TSSA Shutdown'.
    """
    SQL = """
        SELECT id, location, device_type, device_status, license_status, license_expiry
        FROM   elevators
        WHERE  device_status = 'TSSA Shutdown'
        ORDER  BY id
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL)
            rows = [_serialize(dict(r)) for r in cur.fetchall()]
    return {
        "count":  len(rows),
        "rows":   rows,
        "source": "elevators",
    }


# ── Tool 2 ────────────────────────────────────────────────────────────────────

def get_inspection_history(elevator_id: int) -> dict:
    """
    Return all inspections for one elevator, newest first.
    Raises ValueError if elevator_id is not a positive integer.
    """
    _validate_elevator_id(elevator_id)

    SQL = """
        SELECT id,
               inspection_type,
               location,
               earliest_date,
               latest_date,
               outcome,
               customer
        FROM   inspections
        WHERE  elevator_id = %s
        ORDER  BY latest_date DESC NULLS LAST
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL, (elevator_id,))
            rows = [_serialize(dict(r)) for r in cur.fetchall()]
    return {
        "elevator_id": elevator_id,
        "count":       len(rows),
        "rows":        rows,
        "source":      "inspections",
    }


# ── Tool 3 ────────────────────────────────────────────────────────────────────

def count_incidents(year: int) -> dict:
    """
    Return the number of incidents recorded in a given year.
    Raises ValueError if year is outside 1990–present.
    """
    _validate_year(year)

    SQL = """
        SELECT COUNT(*) AS count
        FROM   incidents
        WHERE  EXTRACT(YEAR FROM date_of_occurrence) = %s
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL, (year,))
            row = cur.fetchone()
    return {
        "year":   year,
        "count":  int(row["count"]),
        "source": "incidents",
    }


# ── Tool 4 ────────────────────────────────────────────────────────────────────

def get_incidents_for_elevator(elevator_id: int) -> dict:
    """
    Return all incidents recorded for one elevator, newest first.
    Raises ValueError if elevator_id is not a positive integer.
    """
    _validate_elevator_id(elevator_id)

    SQL = """
        SELECT id,
               category,
               incident_summary,
               date_of_occurrence,
               root_cause,
               narrative
        FROM   incidents
        WHERE  elevator_id = %s
        ORDER  BY date_of_occurrence DESC NULLS LAST
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL, (elevator_id,))
            rows = [_serialize(dict(r)) for r in cur.fetchall()]
    return {
        "elevator_id": elevator_id,
        "count":       len(rows),
        "rows":        rows,
        "source":      "incidents",
    }


# ── Tool 5 ────────────────────────────────────────────────────────────────────

def list_followup_elevators() -> dict:
    """
    Return elevators whose most recent inspection outcome contains 'follow up'
    (case-insensitive). Covers all variants: Follow up, Follow up Major,
    DC Follow up, MCP Follow up, etc.

    Uses DISTINCT ON to select the latest inspection per elevator efficiently.
    """
    SQL = """
        WITH latest AS (
            SELECT DISTINCT ON (elevator_id)
                   elevator_id,
                   latest_date,
                   outcome
            FROM   inspections
            ORDER  BY elevator_id, latest_date DESC NULLS LAST
        )
        SELECT e.id,
               e.location,
               e.device_type,
               e.license_status,
               l.latest_date  AS latest_inspection_date,
               l.outcome      AS latest_outcome
        FROM   latest l
        JOIN   elevators e ON e.id = l.elevator_id
        WHERE  LOWER(l.outcome) LIKE '%%follow up%%'
        ORDER  BY e.id
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL)
            rows = [_serialize(dict(r)) for r in cur.fetchall()]
    return {
        "count":  len(rows),
        "rows":   rows,
        "source": "elevators, inspections",
    }
