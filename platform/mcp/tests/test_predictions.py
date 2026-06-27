"""
Unit tests for tools/predictions.py.

All DB calls are mocked — no real PostgreSQL connection required.
Cases: elevator with a prediction, elevator without one, invalid id.
"""

import datetime
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from tools.predictions import get_risk_explanation, _build_outcome_probabilities


# ── Mock helpers ──────────────────────────────────────────────────────────────

def make_mock_pool(row_or_none):
    """Pool mock where fetchone() returns row_or_none."""
    mock_pool = MagicMock()
    mock_conn = mock_pool.connection.return_value.__enter__.return_value
    mock_cur  = mock_conn.cursor.return_value.__enter__.return_value
    mock_cur.fetchone.return_value = row_or_none
    return mock_pool


# ── Fixtures ──────────────────────────────────────────────────────────────────

_PREDICTION_ROW = {
    "elevator_id":              12345,
    "predicted_outcome":        "Shutdown",
    "confidence":               Decimal("0.712300"),
    "risk_score":               Decimal("0.712300"),
    "risk_level":               "high",
    "model_version":            "v1.0",
    "prediction_date":          datetime.date(2024, 11, 15),
    "risk_explanation":         "Repeated shutdowns and power outages in history.",
    "location":                 "100 King St W, Toronto",
    "device_type":              "Passenger Elevator",
    "license_status":           "ACTIVE",
    # prob columns — only a subset populated to keep fixture concise
    "prob_all_orders_resolved": None,
    "prob_complete":            None,
    "prob_dc_follow_up":        Decimal("0.031200"),
    "prob_fail_initial":        None,
    "prob_follow_up":           Decimal("0.124500"),
    "prob_follow_up_initial":   None,
    "prob_follow_up_major":     Decimal("0.052100"),
    "prob_follow_up_sub_major": None,
    "prob_other":               None,
    "prob_passed":              Decimal("0.079900"),
    "prob_passed_major":        None,
    "prob_shutdown":            Decimal("0.712300"),
    "prob_unable_to_inspect":   None,
}


# ── _build_outcome_probabilities ──────────────────────────────────────────────

class TestBuildOutcomeProbabilities:
    def test_sorted_descending(self):
        probs = _build_outcome_probabilities(_PREDICTION_ROW)
        values = [p["probability"] for p in probs]
        assert values == sorted(values, reverse=True)

    def test_nulls_excluded(self):
        probs = _build_outcome_probabilities(_PREDICTION_ROW)
        cols  = {p["column"] for p in probs}
        # columns with None in the fixture must be absent
        assert "prob_all_orders_resolved" not in cols
        assert "prob_fail_initial" not in cols

    def test_highest_is_shutdown(self):
        probs = _build_outcome_probabilities(_PREDICTION_ROW)
        assert probs[0]["column"] == "prob_shutdown"
        assert probs[0]["probability"] == pytest.approx(0.7123, rel=1e-4)

    def test_label_present(self):
        probs = _build_outcome_probabilities(_PREDICTION_ROW)
        top = probs[0]
        assert top["outcome"] == "Shutdown"

    def test_all_null_row_returns_empty(self):
        null_row = {col: None for col in _PREDICTION_ROW}
        assert _build_outcome_probabilities(null_row) == []


# ── get_risk_explanation: elevator WITH prediction ────────────────────────────

class TestGetRiskExplanationFound:
    def test_found_true(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        assert result["found"] is True

    def test_elevator_id_echoed(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        assert result["elevator_id"] == 12345

    def test_source_field(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        assert result["source"] == "predictions"

    def test_risk_level_returned(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        assert result["risk_level"] == "high"

    def test_risk_score_is_float(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        assert isinstance(result["risk_score"], float)
        assert result["risk_score"] == pytest.approx(0.7123, rel=1e-4)

    def test_confidence_is_float(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        assert isinstance(result["confidence"], float)

    def test_prediction_date_serialized(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        assert result["prediction_date"] == "2024-11-15"

    def test_risk_explanation_text(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        assert "shutdowns" in result["risk_explanation"]

    def test_outcome_probabilities_is_list(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        assert isinstance(result["outcome_probabilities"], list)

    def test_outcome_probabilities_sorted(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        values = [p["probability"] for p in result["outcome_probabilities"]]
        assert values == sorted(values, reverse=True)

    def test_outcome_probabilities_top_is_shutdown(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        assert result["outcome_probabilities"][0]["column"] == "prob_shutdown"

    def test_location_and_device_type(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(_PREDICTION_ROW)):
            result = get_risk_explanation(12345)
        assert result["location"] == "100 King St W, Toronto"
        assert result["device_type"] == "Passenger Elevator"

    def test_null_risk_explanation_preserved(self):
        row = dict(_PREDICTION_ROW, risk_explanation=None)
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(row)):
            result = get_risk_explanation(12345)
        assert result["risk_explanation"] is None


# ── get_risk_explanation: elevator WITHOUT prediction ─────────────────────────

class TestGetRiskExplanationNotFound:
    def test_found_false(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(None)):
            result = get_risk_explanation(99999)
        assert result["found"] is False

    def test_elevator_id_echoed(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(None)):
            result = get_risk_explanation(99999)
        assert result["elevator_id"] == 99999

    def test_message_present(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(None)):
            result = get_risk_explanation(99999)
        assert "No risk prediction" in result["message"]
        assert "99999" in result["message"]

    def test_source_field(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(None)):
            result = get_risk_explanation(99999)
        assert result["source"] == "predictions"

    def test_no_fabricated_factors(self):
        with patch("tools.predictions.get_pool",
                   return_value=make_mock_pool(None)):
            result = get_risk_explanation(99999)
        # must NOT contain risk factors that could mislead
        assert "outcome_probabilities" not in result
        assert "risk_score" not in result
        assert "risk_level" not in result


# ── get_risk_explanation: invalid elevator_id ─────────────────────────────────

class TestGetRiskExplanationInvalidId:
    def test_zero_raises_value_error(self):
        with pytest.raises(ValueError):
            get_risk_explanation(0)

    def test_negative_raises_value_error(self):
        with pytest.raises(ValueError):
            get_risk_explanation(-1)

    def test_bool_raises_type_error(self):
        with pytest.raises(TypeError):
            get_risk_explanation(True)  # type: ignore

    def test_string_raises_type_error(self):
        with pytest.raises(TypeError):
            get_risk_explanation("12345")  # type: ignore

    def test_float_raises_type_error(self):
        with pytest.raises(TypeError):
            get_risk_explanation(1.5)  # type: ignore
