"""
Tests for tools/schedule.py — schedule_inspection.

Unit tests mock all DB calls.
One integration test (skipped if DB not reachable) executes the real INSERT
inside an explicit ROLLBACK so nothing persists.
"""

from __future__ import annotations

import datetime
import os
from unittest.mock import MagicMock, call, patch

import pytest

from tools.schedule import (
    schedule_inspection,
    _validate_date,
    _validate_priority,
    _validate_reason,
    ALLOWED_PRIORITIES,
    REASON_MIN_LEN,
    REASON_MAX_LEN,
)

# ── Integration guard ─────────────────────────────────────────────────────────

_DB_URL = os.environ.get("DATABASE_URL", "postgresql://rocketdash:changeme@localhost:5432/rocketdash")

def _db_reachable() -> bool:
    try:
        import psycopg
        with psycopg.connect(_DB_URL, connect_timeout=2):
            return True
    except Exception:
        return False

integration = pytest.mark.skipif(
    not _db_reachable(),
    reason="PostgreSQL not reachable — skipping integration test",
)

# ── Helpers ───────────────────────────────────────────────────────────────────

_TODAY       = datetime.date.today()
_TOMORROW    = _TODAY + datetime.timedelta(days=1)
_YESTERDAY   = _TODAY - datetime.timedelta(days=1)
_VALID_DATE  = _TOMORROW.isoformat()
_VALID_REASON  = "Annual safety check — overdue by 30 days"
_VALID_ELEV_ID = 63692    # real elevator from the dataset


def _make_mock_pool(elevator_exists: bool, inserted_row: dict | None = None):
    """
    Return a mock ConnectionPool.
    First cursor.fetchone() → elevator existence check.
    Second cursor.execute() → INSERT; cursor.fetchone() → inserted row.
    """
    mock_pool = MagicMock()
    mock_conn = mock_pool.connection.return_value.__enter__.return_value
    mock_cur  = mock_conn.cursor.return_value.__enter__.return_value

    _ELEVATOR_ROW = {"id": _VALID_ELEV_ID} if elevator_exists else None
    _DEFAULT_ROW  = inserted_row or {
        "id":                     6600000,
        "elevator_id":            _VALID_ELEV_ID,
        "inspection_type":        "ED-Periodic Inspection",
        "location":               "55 King St W, Toronto",
        "customer":               "King Street Properties",
        "earliest_date":          _TOMORROW,
        "latest_date":            _TOMORROW,
        "service_request_number": f"SCHEDULED [priority=normal]: {_VALID_REASON}",
        "outcome":                None,
    }
    # fetchone called twice: existence check → INSERT RETURNING
    mock_cur.fetchone.side_effect = [_ELEVATOR_ROW, _DEFAULT_ROW]
    return mock_pool


# ── _validate_date ─────────────────────────────────────────────────────────────

class TestValidateDate:
    def test_today_passes(self):
        assert _validate_date(_TODAY.isoformat()) == _TODAY

    def test_future_string_passes(self):
        assert _validate_date(_VALID_DATE) == _TOMORROW

    def test_future_date_obj_passes(self):
        assert _validate_date(_TOMORROW) == _TOMORROW

    def test_past_raises(self):
        with pytest.raises(ValueError, match="past"):
            _validate_date(_YESTERDAY.isoformat())

    def test_bad_format_raises(self):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            _validate_date("25-12-2026")

    def test_non_string_non_date_raises(self):
        with pytest.raises(TypeError):
            _validate_date(20261225)   # type: ignore

    def test_datetime_rejected(self):
        with pytest.raises(TypeError):
            _validate_date(datetime.datetime.now())  # type: ignore


# ── _validate_priority ────────────────────────────────────────────────────────

class TestValidatePriority:
    def test_valid_priorities(self):
        for p in ALLOWED_PRIORITIES:
            assert _validate_priority(p) == p

    def test_mixed_case_normalised(self):
        assert _validate_priority("HIGH") == "high"
        assert _validate_priority("Normal") == "normal"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="priority"):
            _validate_priority("critical")

    def test_non_string_raises(self):
        with pytest.raises(TypeError):
            _validate_priority(1)  # type: ignore


# ── _validate_reason ──────────────────────────────────────────────────────────

class TestValidateReason:
    def test_valid_reason_passes(self):
        r = _validate_reason("  overdue annual check  ")
        assert r == "overdue annual check"

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match=str(REASON_MIN_LEN)):
            _validate_reason("hi")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match=str(REASON_MAX_LEN)):
            _validate_reason("x" * (REASON_MAX_LEN + 1))

    def test_exactly_min_length_passes(self):
        _validate_reason("x" * REASON_MIN_LEN)

    def test_non_string_raises(self):
        with pytest.raises(TypeError):
            _validate_reason(42)  # type: ignore


# ── schedule_inspection — unit tests ──────────────────────────────────────────

class TestScheduleInspectionUnit:
    def test_valid_insert_returns_row(self):
        with patch("tools.schedule.get_pool", return_value=_make_mock_pool(True)):
            result = schedule_inspection(_VALID_ELEV_ID, _VALID_DATE, _VALID_REASON)
        assert result["id"] == 6600000
        assert result["elevator_id"] == _VALID_ELEV_ID
        assert result["source"] == "inspections table"

    def test_echoes_priority_and_reason(self):
        with patch("tools.schedule.get_pool", return_value=_make_mock_pool(True)):
            result = schedule_inspection(_VALID_ELEV_ID, _VALID_DATE, _VALID_REASON, priority="high")
        assert result["priority"] == "high"
        assert result["reason"] == _VALID_REASON

    def test_dates_serialised_to_strings(self):
        with patch("tools.schedule.get_pool", return_value=_make_mock_pool(True)):
            result = schedule_inspection(_VALID_ELEV_ID, _VALID_DATE, _VALID_REASON)
        assert result["earliest_date"] == _TOMORROW.isoformat()
        assert result["latest_date"] == _TOMORROW.isoformat()

    def test_outcome_is_none(self):
        with patch("tools.schedule.get_pool", return_value=_make_mock_pool(True)):
            result = schedule_inspection(_VALID_ELEV_ID, _VALID_DATE, _VALID_REASON)
        assert result["outcome"] is None

    def test_inspection_type_is_periodic(self):
        with patch("tools.schedule.get_pool", return_value=_make_mock_pool(True)):
            result = schedule_inspection(_VALID_ELEV_ID, _VALID_DATE, _VALID_REASON)
        assert result["inspection_type"] == "ED-Periodic Inspection"

    # ── invalid elevator_id ──

    def test_elevator_id_zero_raises(self):
        with pytest.raises(ValueError):
            schedule_inspection(0, _VALID_DATE, _VALID_REASON)

    def test_elevator_id_negative_raises(self):
        with pytest.raises(ValueError):
            schedule_inspection(-1, _VALID_DATE, _VALID_REASON)

    def test_elevator_id_bool_raises(self):
        with pytest.raises(TypeError):
            schedule_inspection(True, _VALID_DATE, _VALID_REASON)   # type: ignore

    def test_elevator_id_string_raises(self):
        with pytest.raises(TypeError):
            schedule_inspection("12345", _VALID_DATE, _VALID_REASON)  # type: ignore

    # ── invalid date ──

    def test_past_date_raises_before_db(self):
        """Validation must fire before any DB call."""
        mock_pool = MagicMock()
        with patch("tools.schedule.get_pool", return_value=mock_pool):
            with pytest.raises(ValueError, match="past"):
                schedule_inspection(_VALID_ELEV_ID, _YESTERDAY.isoformat(), _VALID_REASON)
        mock_pool.connection.assert_not_called()

    def test_bad_date_format_raises(self):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            schedule_inspection(_VALID_ELEV_ID, "12/31/2026", _VALID_REASON)

    # ── unknown elevator ──

    def test_unknown_elevator_raises(self):
        with patch("tools.schedule.get_pool", return_value=_make_mock_pool(elevator_exists=False)):
            with pytest.raises(ValueError, match="does not exist"):
                schedule_inspection(999999999, _VALID_DATE, _VALID_REASON)

    # ── invalid priority ──

    def test_bad_priority_raises_before_db(self):
        mock_pool = MagicMock()
        with patch("tools.schedule.get_pool", return_value=mock_pool):
            with pytest.raises(ValueError, match="priority"):
                schedule_inspection(_VALID_ELEV_ID, _VALID_DATE, _VALID_REASON, priority="extreme")
        mock_pool.connection.assert_not_called()

    # ── invalid reason ──

    def test_empty_reason_raises(self):
        with pytest.raises(ValueError):
            schedule_inspection(_VALID_ELEV_ID, _VALID_DATE, "")

    def test_whitespace_reason_raises(self):
        with pytest.raises(ValueError):
            schedule_inspection(_VALID_ELEV_ID, _VALID_DATE, "   ")

    def test_reason_too_long_raises_before_db(self):
        mock_pool = MagicMock()
        with patch("tools.schedule.get_pool", return_value=mock_pool):
            with pytest.raises(ValueError, match=str(REASON_MAX_LEN)):
                schedule_inspection(_VALID_ELEV_ID, _VALID_DATE, "x" * (REASON_MAX_LEN + 1))
        mock_pool.connection.assert_not_called()


# ── Integration test — real DB, explicit ROLLBACK ────────────────────────────

class TestScheduleInspectionIntegration:
    @integration
    def test_valid_insert_rolled_back(self):
        """
        Execute the real INSERT inside an explicit transaction and roll it back,
        verifying the returned row has correct structure without persisting data.
        """
        import psycopg
        from psycopg.rows import dict_row
        from tools.schedule import _INSERT_SQL, _ELEVATOR_EXISTS_SQL, SCHEDULED_TYPE, _validate_date, _validate_reason, _validate_priority, _serialize
        from tools.elevators import _validate_elevator_id

        elevator_id   = _VALID_ELEV_ID
        scheduled_date = _TOMORROW
        reason        = _VALID_REASON
        priority      = "high"
        srn           = f"SCHEDULED [priority={priority}]: {reason}"

        with psycopg.connect(_DB_URL, row_factory=dict_row) as conn:
            conn.autocommit = False
            try:
                with conn.cursor() as cur:
                    # Verify elevator exists
                    cur.execute(_ELEVATOR_EXISTS_SQL, (elevator_id,))
                    assert cur.fetchone() is not None, f"Elevator {elevator_id} not found"

                    cur.execute(
                        _INSERT_SQL,
                        {
                            "elevator_id":            elevator_id,
                            "inspection_type":        SCHEDULED_TYPE,
                            "scheduled_date":         scheduled_date,
                            "service_request_number": srn,
                        },
                    )
                    row = dict(cur.fetchone())

                # Assert on the returned row before rolling back
                assert row["elevator_id"] == elevator_id
                assert row["earliest_date"] == scheduled_date
                assert row["latest_date"] == scheduled_date
                assert row["inspection_type"] == SCHEDULED_TYPE
                assert row["service_request_number"] == srn
                assert row["outcome"] is None
                assert isinstance(row["id"], int)
                assert row["id"] > 0

            finally:
                conn.rollback()   # ← nothing persists
