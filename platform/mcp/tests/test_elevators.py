"""
Unit tests for tools/elevators.py.

All DB calls are mocked — no real PostgreSQL connection required.
Each tool is tested for: happy path, empty result, and invalid input.
"""

import datetime
import pytest
from unittest.mock import MagicMock, patch

from tools.elevators import (
    list_tssa_shutdown_elevators,
    get_inspection_history,
    count_incidents,
    get_incidents_for_elevator,
    list_followup_elevators,
    _validate_elevator_id,
    _validate_year,
)


# ── Mock helpers ──────────────────────────────────────────────────────────────

def make_mock_pool(rows):
    """
    Return a MagicMock that behaves like a psycopg ConnectionPool.
    pool.connection() → conn (context mgr)
    conn.cursor(row_factory=...) → cur (context mgr)
    cur.fetchall() → rows
    cur.fetchone() → rows[0] if rows else None
    """
    mock_pool = MagicMock()
    mock_conn = mock_pool.connection.return_value.__enter__.return_value
    mock_cur  = mock_conn.cursor.return_value.__enter__.return_value
    mock_cur.fetchall.return_value  = rows
    mock_cur.fetchone.return_value  = rows[0] if rows else None
    return mock_pool


# ── Validation unit tests ─────────────────────────────────────────────────────

class TestValidateElevatorId:
    def test_positive_int_passes(self):
        _validate_elevator_id(1)
        _validate_elevator_id(99999)

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            _validate_elevator_id(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            _validate_elevator_id(-5)

    def test_bool_raises(self):
        with pytest.raises(TypeError):
            _validate_elevator_id(True)

    def test_string_raises(self):
        with pytest.raises(TypeError):
            _validate_elevator_id("12345")  # type: ignore


class TestValidateYear:
    def test_valid_year_passes(self):
        _validate_year(2023)
        _validate_year(1990)

    def test_too_early_raises(self):
        with pytest.raises(ValueError):
            _validate_year(1989)

    def test_future_raises(self):
        with pytest.raises(ValueError):
            _validate_year(datetime.date.today().year + 1)

    def test_bool_raises(self):
        with pytest.raises(TypeError):
            _validate_year(True)


# ── Tool 1: list_tssa_shutdown_elevators ─────────────────────────────────────

class TestListTssaShutdownElevators:
    _rows = [
        {"id": 100, "location": "100 King St W", "device_type": "Passenger Elevator",
         "device_status": "TSSA Shutdown", "license_status": "ACTIVE", "license_expiry": None},
        {"id": 200, "location": "200 Queen St E", "device_type": "Freight Elevator",
         "device_status": "TSSA Shutdown", "license_status": "INACTIVE", "license_expiry": None},
    ]

    def test_returns_rows_and_count(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_tssa_shutdown_elevators()
        assert result["count"] == 2
        assert result["source"] == "elevators"
        assert result["rows"][0]["id"] == 100

    def test_empty_result(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool([])):
            result = list_tssa_shutdown_elevators()
        assert result["count"] == 0
        assert result["rows"] == []

    def test_dates_serialized(self):
        rows_with_date = [
            {"id": 1, "location": "X", "device_type": "Y", "device_status": "TSSA Shutdown",
             "license_status": "ACTIVE", "license_expiry": datetime.date(2025, 1, 15)}
        ]
        with patch("tools.elevators.get_pool", return_value=make_mock_pool(rows_with_date)):
            result = list_tssa_shutdown_elevators()
        assert result["rows"][0]["license_expiry"] == "2025-01-15"


# ── Tool 2: get_inspection_history ────────────────────────────────────────────

class TestGetInspectionHistory:
    _rows = [
        {"id": 501, "inspection_type": "Periodic", "location": "Floor 3",
         "earliest_date": datetime.date(2024, 1, 1), "latest_date": datetime.date(2024, 3, 15),
         "outcome": "Passed", "customer": "Acme Corp"},
        {"id": 400, "inspection_type": "Follow-up", "location": "Floor 3",
         "earliest_date": datetime.date(2023, 6, 1), "latest_date": datetime.date(2023, 6, 10),
         "outcome": "Follow up", "customer": "Acme Corp"},
    ]

    def test_returns_history(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool(self._rows)):
            result = get_inspection_history(12345)
        assert result["elevator_id"] == 12345
        assert result["count"] == 2
        assert result["source"] == "inspections"
        assert result["rows"][0]["outcome"] == "Passed"

    def test_empty_history(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool([])):
            result = get_inspection_history(99999)
        assert result["count"] == 0

    def test_dates_serialized(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool(self._rows)):
            result = get_inspection_history(12345)
        assert result["rows"][0]["latest_date"] == "2024-03-15"

    def test_invalid_id_zero(self):
        with pytest.raises(ValueError):
            get_inspection_history(0)

    def test_invalid_id_negative(self):
        with pytest.raises(ValueError):
            get_inspection_history(-1)

    def test_invalid_id_string(self):
        with pytest.raises(TypeError):
            get_inspection_history("abc")  # type: ignore


# ── Tool 3: count_incidents ───────────────────────────────────────────────────

class TestCountIncidents:
    def test_returns_count(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool([{"count": 42}])):
            result = count_incidents(2023)
        assert result["year"] == 2023
        assert result["count"] == 42
        assert result["source"] == "incidents"

    def test_zero_incidents(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool([{"count": 0}])):
            result = count_incidents(2000)
        assert result["count"] == 0

    def test_invalid_year_too_early(self):
        with pytest.raises(ValueError):
            count_incidents(1980)

    def test_invalid_year_future(self):
        with pytest.raises(ValueError):
            count_incidents(datetime.date.today().year + 5)

    def test_invalid_year_bool(self):
        with pytest.raises(TypeError):
            count_incidents(True)  # type: ignore


# ── Tool 4: get_incidents_for_elevator ───────────────────────────────────────

class TestGetIncidentsForElevator:
    _rows = [
        {"id": 1001, "category": "Entrapment", "incident_summary": "Doors jammed",
         "date_of_occurrence": datetime.date(2023, 8, 20), "root_cause": "Mechanical failure",
         "narrative": "Passenger trapped between floors."},
    ]

    def test_returns_incidents(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool(self._rows)):
            result = get_incidents_for_elevator(12345)
        assert result["elevator_id"] == 12345
        assert result["count"] == 1
        assert result["source"] == "incidents"
        assert result["rows"][0]["category"] == "Entrapment"

    def test_empty_result(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool([])):
            result = get_incidents_for_elevator(99999)
        assert result["count"] == 0
        assert result["rows"] == []

    def test_dates_serialized(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool(self._rows)):
            result = get_incidents_for_elevator(12345)
        assert result["rows"][0]["date_of_occurrence"] == "2023-08-20"

    def test_invalid_id_zero(self):
        with pytest.raises(ValueError):
            get_incidents_for_elevator(0)

    def test_invalid_id_negative(self):
        with pytest.raises(ValueError):
            get_incidents_for_elevator(-100)


# ── Tool 5: list_followup_elevators ──────────────────────────────────────────

class TestListFollowupElevators:
    _rows = [
        {"id": 300, "location": "300 Yonge St", "device_type": "Passenger Elevator",
         "license_status": "ACTIVE",
         "latest_inspection_date": datetime.date(2024, 5, 10),
         "latest_outcome": "Follow up"},
        {"id": 400, "location": "400 Bay St", "device_type": "Freight Elevator",
         "license_status": "ACTIVE",
         "latest_inspection_date": datetime.date(2024, 4, 1),
         "latest_outcome": "Follow up Major"},
    ]

    def test_returns_followup_elevators(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_followup_elevators()
        assert result["count"] == 2
        assert result["source"] == "elevators, inspections"
        assert result["rows"][1]["latest_outcome"] == "Follow up Major"

    def test_empty_result(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool([])):
            result = list_followup_elevators()
        assert result["count"] == 0
        assert result["rows"] == []

    def test_dates_serialized(self):
        with patch("tools.elevators.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_followup_elevators()
        assert result["rows"][0]["latest_inspection_date"] == "2024-05-10"
