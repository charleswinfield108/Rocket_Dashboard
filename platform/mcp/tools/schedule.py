"""
MCP tool: schedule_inspection

⚠️  DESTRUCTIVE TOOL — writes to the inspections table.
This tool must only be called after explicit user confirmation.
Confirmation is enforced in the Go API / system-prompt layer (AND-209/AND-210);
the tool itself performs the validated write unconditionally once called.

The inspections table has no SERIAL sequence (IDs were loaded from TSSA source data).
A CTE selects MAX(id)+1 inside the same statement to generate the new ID atomically
within the transaction. Low write concurrency on this operations tool makes this safe.

Mapping to inspections columns:
  elevator_id           → elevators FK (validated to exist)
  earliest_date         → scheduled date
  latest_date           → scheduled date
  inspection_type       → "ED-Periodic Inspection" (scheduled periodic)
  service_request_number→ "SCHEDULED [priority=P]: reason" (encodes both fields)
  location              → copied from elevators.location at insert time
  customer              → copied from elevators.license_holder at insert time
  outcome               → NULL (inspection not yet completed)
"""

from __future__ import annotations

import datetime

from psycopg.rows import dict_row

from db import get_pool
from tools.elevators import _validate_elevator_id, _serialize

# ── Constants ──────────────────────────────────────────────────────────────────

ALLOWED_PRIORITIES = {"low", "normal", "high", "urgent"}
REASON_MIN_LEN     = 5
REASON_MAX_LEN     = 500
SCHEDULED_TYPE     = "ED-Periodic Inspection"


# ── Validation helpers ─────────────────────────────────────────────────────────

def _validate_date(date: str | datetime.date) -> datetime.date:
    """
    Parse and validate the scheduled date.

    Accepts a datetime.date or an ISO-format string ("YYYY-MM-DD").
    The date must be today or in the future — scheduling a past inspection
    makes no operational sense and is rejected.
    """
    if isinstance(date, datetime.date) and not isinstance(date, datetime.datetime):
        parsed = date
    elif isinstance(date, str):
        try:
            parsed = datetime.date.fromisoformat(date.strip())
        except ValueError:
            raise ValueError(
                f"date must be in YYYY-MM-DD format, got {date!r}"
            )
    else:
        raise TypeError(
            f"date must be a string or datetime.date, got {type(date).__name__}"
        )

    today = datetime.date.today()
    if parsed < today:
        raise ValueError(
            f"Scheduled date {parsed.isoformat()} is in the past. "
            f"Today is {today.isoformat()}. Provide a present or future date."
        )
    return parsed


def _validate_priority(priority: str) -> str:
    """Return the lowercased priority or raise ValueError."""
    if not isinstance(priority, str):
        raise TypeError(
            f"priority must be a string, got {type(priority).__name__}"
        )
    p = priority.strip().lower()
    if p not in ALLOWED_PRIORITIES:
        raise ValueError(
            f"priority must be one of {sorted(ALLOWED_PRIORITIES)}, got {priority!r}"
        )
    return p


def _validate_reason(reason: str) -> str:
    """Return the stripped reason or raise ValueError."""
    if not isinstance(reason, str):
        raise TypeError(
            f"reason must be a string, got {type(reason).__name__}"
        )
    r = reason.strip()
    if len(r) < REASON_MIN_LEN:
        raise ValueError(
            f"reason must be at least {REASON_MIN_LEN} characters, got {len(r)!r}"
        )
    if len(r) > REASON_MAX_LEN:
        raise ValueError(
            f"reason must be at most {REASON_MAX_LEN} characters, got {len(r)}"
        )
    return r


# ── Tool ──────────────────────────────────────────────────────────────────────

_INSERT_SQL = """
WITH new_id AS (
    -- Generate next ID within this statement. Safe for the low concurrency of
    -- an operations scheduling tool; a real-time system should use a SEQUENCE.
    SELECT COALESCE(MAX(id), 0) + 1 AS id FROM inspections
)
INSERT INTO inspections (
    id,
    elevator_id,
    inspection_type,
    location,
    customer,
    earliest_date,
    latest_date,
    service_request_number,
    outcome
)
SELECT
    new_id.id,
    %(elevator_id)s,
    %(inspection_type)s,
    e.location,
    e.license_holder,
    %(scheduled_date)s,
    %(scheduled_date)s,
    %(service_request_number)s,
    NULL
FROM new_id
CROSS JOIN elevators e
WHERE e.id = %(elevator_id)s
RETURNING
    id,
    elevator_id,
    inspection_type,
    location,
    customer,
    earliest_date,
    latest_date,
    service_request_number,
    outcome
"""

_ELEVATOR_EXISTS_SQL = """
SELECT id FROM elevators WHERE id = %s LIMIT 1
"""


def schedule_inspection(
    elevator_id: int,
    date: str | datetime.date,
    reason: str,
    priority: str = "normal",
) -> dict:
    """
    Schedule a periodic inspection for one elevator by inserting a row into
    the inspections table.

    ⚠️  This tool performs an immediate write to the database. It must only be
    invoked after the user has confirmed the action (enforced upstream in AND-209).

    Args:
        elevator_id: ID of the elevator to inspect (must exist in elevators table)
        date:        Scheduled date as ISO string "YYYY-MM-DD" or datetime.date;
                     must be today or in the future
        reason:      Why this inspection is being scheduled (5–500 characters)
        priority:    One of "low", "normal", "high", "urgent" (default "normal")

    Returns:
        dict with the inserted row (including new id) and source = "inspections table"

    Raises:
        TypeError:  if elevator_id is not int, date is wrong type, etc.
        ValueError: if date is in the past, priority is unknown, elevator not found, etc.
    """
    # ── Validate inputs before touching the DB ────────────────────────────────
    _validate_elevator_id(elevator_id)
    parsed_date = _validate_date(date)
    clean_reason = _validate_reason(reason)
    clean_priority = _validate_priority(priority)

    # Encode both priority and reason into service_request_number.
    # The inspections table has no dedicated priority or notes column.
    srn = f"SCHEDULED [priority={clean_priority}]: {clean_reason}"

    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:

            # Confirm the elevator exists (gives a clear error instead of a
            # silent 0-row INSERT when the CTE WHERE clause matches nothing)
            cur.execute(_ELEVATOR_EXISTS_SQL, (elevator_id,))
            if cur.fetchone() is None:
                raise ValueError(
                    f"Elevator {elevator_id} does not exist in the elevators table. "
                    "Check the elevator ID and try again."
                )

            cur.execute(
                _INSERT_SQL,
                {
                    "elevator_id":          elevator_id,
                    "inspection_type":      SCHEDULED_TYPE,
                    "scheduled_date":       parsed_date,
                    "service_request_number": srn,
                },
            )
            row = cur.fetchone()

        # commit happens automatically when the connection context manager exits

    return {
        **_serialize(dict(row)),
        "priority": clean_priority,
        "reason":   clean_reason,
        "source":   "inspections table",
    }
