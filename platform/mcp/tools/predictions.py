"""
MCP tool: get_risk_explanation

Returns structured risk prediction data for one elevator from the
predictions table. Covers 40,809 of 45,383 elevators; the remaining
~4,574 receive an explicit "no prediction available" response so the
chatbot never fabricates risk factors.

All SQL uses bound parameters. Returns a `source` field for citation.
"""

import datetime
from decimal import Decimal

from psycopg.rows import dict_row

from db import get_pool
from tools.elevators import _validate_elevator_id


# ordered list of per-outcome probability columns in the table
_PROB_COLUMNS = [
    "prob_all_orders_resolved",
    "prob_complete",
    "prob_dc_follow_up",
    "prob_fail_initial",
    "prob_follow_up",
    "prob_follow_up_initial",
    "prob_follow_up_major",
    "prob_follow_up_sub_major",
    "prob_other",
    "prob_passed",
    "prob_passed_major",
    "prob_shutdown",
    "prob_unable_to_inspect",
]

# Human-readable labels for each outcome column
_PROB_LABELS = {
    "prob_all_orders_resolved":  "All orders resolved",
    "prob_complete":             "Complete",
    "prob_dc_follow_up":         "DC follow-up",
    "prob_fail_initial":         "Fail initial",
    "prob_follow_up":            "Follow-up",
    "prob_follow_up_initial":    "Follow-up initial",
    "prob_follow_up_major":      "Follow-up major",
    "prob_follow_up_sub_major":  "Follow-up sub-major",
    "prob_other":                "Other",
    "prob_passed":               "Passed",
    "prob_passed_major":         "Passed major",
    "prob_shutdown":             "Shutdown",
    "prob_unable_to_inspect":    "Unable to inspect",
}

_SQL = """
    SELECT p.elevator_id,
           p.predicted_outcome,
           p.confidence,
           p.risk_score,
           p.risk_level,
           p.model_version,
           p.prediction_date,
           p.risk_explanation,
           p.prob_all_orders_resolved,
           p.prob_complete,
           p.prob_dc_follow_up,
           p.prob_fail_initial,
           p.prob_follow_up,
           p.prob_follow_up_initial,
           p.prob_follow_up_major,
           p.prob_follow_up_sub_major,
           p.prob_other,
           p.prob_passed,
           p.prob_passed_major,
           p.prob_shutdown,
           p.prob_unable_to_inspect,
           e.location,
           e.device_type,
           e.license_status
    FROM   predictions p
    JOIN   elevators   e ON e.id = p.elevator_id
    WHERE  p.elevator_id = %s
"""


def _build_outcome_probabilities(row: dict) -> list[dict]:
    """
    Extract the per-outcome probability columns into a sorted list of dicts,
    highest probability first. Skips columns whose value is NULL.
    """
    probs = []
    for col in _PROB_COLUMNS:
        val = row.get(col)
        if val is None:
            continue
        probs.append({
            "outcome":     _PROB_LABELS[col],
            "column":      col,
            "probability": round(float(val), 6),
        })
    probs.sort(key=lambda x: x["probability"], reverse=True)
    return probs


def get_risk_explanation(elevator_id: int) -> dict:
    """
    Return the risk prediction and per-outcome probability breakdown for one
    elevator. Structured risk factors are returned individually so a chatbot
    can cite specific numbers rather than just a summary label.

    If the elevator has no prediction row, returns found=False with an
    explicit message — the tool never fabricates risk factors.

    Raises ValueError if elevator_id is not a positive integer.
    Raises TypeError if elevator_id is not an int (e.g. bool, string).
    """
    _validate_elevator_id(elevator_id)

    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(_SQL, (elevator_id,))
            row = cur.fetchone()

    if row is None:
        return {
            "elevator_id": elevator_id,
            "found":       False,
            "message":     (
                f"No risk prediction is available for elevator {elevator_id}. "
                "The predictions model covers approximately 40,800 of 45,383 "
                "elevators in the Ontario fleet."
            ),
            "source": "predictions",
        }

    row = dict(row)

    # Serialise date
    prediction_date = row.get("prediction_date")
    if isinstance(prediction_date, datetime.date):
        prediction_date = prediction_date.isoformat()

    return {
        "elevator_id":        elevator_id,
        "found":              True,
        "location":           row.get("location"),
        "device_type":        row.get("device_type"),
        "license_status":     row.get("license_status"),
        "risk_level":         row.get("risk_level"),
        "risk_score":         round(float(row["risk_score"]), 6),
        "predicted_outcome":  row.get("predicted_outcome"),
        "confidence":         round(float(row["confidence"]), 6),
        "risk_explanation":   row.get("risk_explanation"),
        "outcome_probabilities": _build_outcome_probabilities(row),
        "model_version":      row.get("model_version"),
        "prediction_date":    prediction_date,
        "source":             "predictions",
    }
