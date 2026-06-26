"""
Unit tests for tools/additional.py.

All DB calls are mocked — no real PostgreSQL connection required.
Each tool is tested for: happy path, empty result, and invalid input.
"""

import datetime
import pytest
from unittest.mock import MagicMock, patch

from tools.additional import (
    list_expiring_licences,
    list_overdue_inspections,
    get_incident_root_cause_summary,
    list_alterations_pending_followup,
    _validate_days,
)


# ── Mock helpers ──────────────────────────────────────────────────────────────

def make_mock_pool(rows):
    mock_pool = MagicMock()
    mock_conn = mock_pool.connection.return_value.__enter__.return_value
    mock_cur  = mock_conn.cursor.return_value.__enter__.return_value
    mock_cur.fetchall.return_value  = rows
    mock_cur.fetchone.return_value  = rows[0] if rows else None
    return mock_pool


# ── Validation: _validate_days ────────────────────────────────────────────────

class TestValidateDays:
    def test_positive_passes(self):
        _validate_days(1)
        _validate_days(90)
        _validate_days(3650)

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            _validate_days(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            _validate_days(-10)

    def test_over_max_raises(self):
        with pytest.raises(ValueError):
            _validate_days(3651)

    def test_bool_raises(self):
        with pytest.raises(TypeError):
            _validate_days(True)

    def test_string_raises(self):
        with pytest.raises(TypeError):
            _validate_days("90")  # type: ignore


# ── Tool A: list_expiring_licences ────────────────────────────────────────────

class TestListExpiringLicences:
    _rows = [
        {"id": 10, "location": "55 King St W", "device_type": "Passenger Elevator",
         "license_status": "ACTIVE", "license_expiry": datetime.date(2026, 7, 15),
         "license_holder": "Acme Realty"},
        {"id": 20, "location": "200 Bay St", "device_type": "Freight Elevator",
         "license_status": "ACTIVE", "license_expiry": datetime.date(2026, 8, 1),
         "license_holder": "Bay Properties"},
    ]

    def test_returns_rows_and_count(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_expiring_licences(90)
        assert result["count"] == 2
        assert result["days_window"] == 90
        assert result["source"] == "elevators"
        assert result["rows"][0]["location"] == "55 King St W"

    def test_empty_result(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool([])):
            result = list_expiring_licences(30)
        assert result["count"] == 0
        assert result["rows"] == []

    def test_default_days(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool([])):
            result = list_expiring_licences()
        assert result["days_window"] == 90

    def test_dates_serialized(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_expiring_licences(90)
        assert result["rows"][0]["license_expiry"] == "2026-07-15"

    def test_invalid_days_zero(self):
        with pytest.raises(ValueError):
            list_expiring_licences(0)

    def test_invalid_days_too_large(self):
        with pytest.raises(ValueError):
            list_expiring_licences(9999)

    def test_invalid_days_bool(self):
        with pytest.raises(TypeError):
            list_expiring_licences(True)  # type: ignore


# ── Tool B: list_overdue_inspections ─────────────────────────────────────────

class TestListOverdueInspections:
    _rows = [
        {"id": 101, "location": "123 Elm St", "device_type": "Passenger Elevator",
         "license_status": "ACTIVE",
         "last_inspection_date": None,
         "days_since_inspection": None},
        {"id": 202, "location": "456 Oak Ave", "device_type": "Freight Elevator",
         "license_status": "ACTIVE",
         "last_inspection_date": datetime.date(2021, 3, 1),
         "days_since_inspection": 1943},
    ]

    def test_returns_rows_and_meta(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_overdue_inspections(365)
        assert result["count"] == 2
        assert result["days_threshold"] == 365
        assert result["limit"] == 100
        assert result["source"] == "elevators, inspections"

    def test_never_inspected_elevator_present(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_overdue_inspections(365)
        assert result["rows"][0]["last_inspection_date"] is None

    def test_dates_serialized(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_overdue_inspections(365)
        assert result["rows"][1]["last_inspection_date"] == "2021-03-01"

    def test_empty_result(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool([])):
            result = list_overdue_inspections(180)
        assert result["count"] == 0
        assert result["rows"] == []

    def test_default_args(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool([])):
            result = list_overdue_inspections()
        assert result["days_threshold"] == 365
        assert result["limit"] == 100

    def test_custom_limit(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_overdue_inspections(365, limit=10)
        assert result["limit"] == 10

    def test_invalid_days_zero(self):
        with pytest.raises(ValueError):
            list_overdue_inspections(0)

    def test_invalid_days_bool(self):
        with pytest.raises(TypeError):
            list_overdue_inspections(True)  # type: ignore

    def test_invalid_limit_zero(self):
        with pytest.raises(ValueError):
            list_overdue_inspections(365, limit=0)

    def test_invalid_limit_over_max(self):
        with pytest.raises(ValueError):
            list_overdue_inspections(365, limit=501)

    def test_invalid_limit_bool(self):
        with pytest.raises(ValueError):
            list_overdue_inspections(365, limit=True)


# ── Tool C: get_incident_root_cause_summary ───────────────────────────────────

class TestGetIncidentRootCauseSummary:
    _rows = [
        {"root_cause": "Unknown / Not recorded", "count": 1586, "percentage": 66.4},
        {"root_cause": "8.2 Utilities (power, water, telecomm, sewage)", "count": 248, "percentage": 10.4},
        {"root_cause": "1.2 Defective or failed component including safety devices", "count": 216, "percentage": 9.0},
    ]

    def test_returns_breakdown_and_total(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = get_incident_root_cause_summary()
        assert result["total_incidents"] == 2050
        assert result["source"] == "incidents"
        assert len(result["breakdown"]) == 3

    def test_top_cause_is_first(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = get_incident_root_cause_summary()
        assert result["breakdown"][0]["root_cause"] == "Unknown / Not recorded"
        assert result["breakdown"][0]["count"] == 1586

    def test_numeric_types(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = get_incident_root_cause_summary()
        row = result["breakdown"][0]
        assert isinstance(row["count"], int)
        assert isinstance(row["percentage"], float)

    def test_empty_incidents_table(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool([])):
            result = get_incident_root_cause_summary()
        assert result["total_incidents"] == 0
        assert result["breakdown"] == []


# ── Tool D: list_alterations_pending_followup ─────────────────────────────────

class TestListAlterationsPendingFollowup:
    _rows = [
        {"id": 5001, "elevator_id": 300, "location": "300 Yonge St",
         "device_type": "Passenger Elevator", "alteration_type": "ED-Minor A Alteration",
         "summary": "Replace door motor", "status": "Pending Follow Up",
         "customer": "Toronto Properties Inc"},
        {"id": 5002, "elevator_id": 300, "location": "300 Yonge St",
         "device_type": "Passenger Elevator", "alteration_type": "ED-Major Alteration",
         "summary": "Full cab renovation", "status": "Pending Follow Up",
         "customer": "Toronto Properties Inc"},
    ]

    def test_returns_rows_and_count(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_alterations_pending_followup()
        assert result["count"] == 2
        assert result["source"] == "alterations, elevators"
        assert result["rows"][0]["alteration_type"] == "ED-Minor A Alteration"

    def test_empty_result(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool([])):
            result = list_alterations_pending_followup()
        assert result["count"] == 0
        assert result["rows"] == []

    def test_all_rows_have_pending_status(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_alterations_pending_followup()
        for row in result["rows"]:
            assert row["status"] == "Pending Follow Up"

    def test_elevator_id_present(self):
        with patch("tools.additional.get_pool", return_value=make_mock_pool(self._rows)):
            result = list_alterations_pending_followup()
        assert result["rows"][0]["elevator_id"] == 300
