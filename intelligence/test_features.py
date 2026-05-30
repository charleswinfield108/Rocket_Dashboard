"""
TDD tests for the feature engineering pipeline (AND-103 Task 5).

All tests load data/feature_matrix.csv produced by Step 7 of
intelligence/feature_engineering.ipynb. They will fail with a
FileNotFoundError until the notebook is executed and the CSV is written.

Manual verification performed against raw data before implementation:

Elevator 17489 — 24 inspections total; used for date-boundary checks.
For the inspection dated 2014-02-12 (InspectionNumber 4794466):
  Prior inspections (Latest_INSPECTION_Date < 2014-02-12): 9 rows
    2012-02-23 Shutdown, 2012-03-05 Shutdown, 2012-03-07 Shutdown,
    2012-03-08 Shutdown, 2012-03-16 Passed, 2013-10-24 Follow up ×2,
    2014-01-29 All Orders Resolved, 2014-01-29 Follow up
  Outcome-class breakdown: prior_pass_count=2, prior_followup_count=3, prior_fail_count=4
  Orders linked to prior inspections: 15
  Orders linked to current/future inspections (must be excluded): 20

Elevator 23920 — exactly 1 inspection in the dataset (2011-01-10, Passed).
  No prior history exists; all lookback features must be 0 or NaN.
"""

import math

import pandas as pd
import pytest

FEATURE_MATRIX_PATH = "data/feature_matrix.csv"
INSPECTION_PATH = "data/inspection.csv"
ORDER_PATH = "data/order.csv"


@pytest.fixture(scope="module")
def fm():
    df = pd.read_csv(FEATURE_MATRIX_PATH, parse_dates=["Latest_INSPECTION_Date"])
    return df


@pytest.fixture(scope="module")
def raw_inspection():
    return pd.read_csv(INSPECTION_PATH, parse_dates=["Latest_INSPECTION_Date"])


@pytest.fixture(scope="module")
def raw_orders():
    df = pd.read_csv(ORDER_PATH)
    df["DateofIssue"] = pd.to_datetime(df["DateofIssue"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Test 1 — Prior-inspection features must not include the current inspection
#           or any later inspection for that elevator.
# ---------------------------------------------------------------------------

class TestNoPriorFeatureUsesCurrentOrFutureInspection:
    """
    Elevator 17489, inspection date 2014-02-12.

    Manually counted prior inspections (date < 2014-02-12): 9 total.
    Class breakdown: Pass=2, Follow Up=3, Fail/Shutdown=4.

    Any count that exceeds these values — or sums to more than 9 — indicates
    the pipeline included the current inspection or later ones in its aggregate.
    """

    ELEV_ID = 17489
    TARGET_DATE = pd.Timestamp("2014-02-12")

    def _get_row(self, fm):
        mask = (
            (fm["ElevatingDevicesNumber"] == self.ELEV_ID)
            & (fm["Latest_INSPECTION_Date"] == self.TARGET_DATE)
        )
        rows = fm[mask]
        assert len(rows) == 1, (
            f"Expected exactly 1 feature-matrix row for elevator {self.ELEV_ID} "
            f"on {self.TARGET_DATE.date()}; found {len(rows)}"
        )
        return rows.iloc[0]

    def test_prior_pass_count(self, fm):
        row = self._get_row(fm)
        assert row["prior_pass_count"] == 2, (
            "Elevator 17489 had 2 prior Pass outcomes before 2014-02-12: "
            "2012-03-16 (Passed) and 2014-01-29 (All Orders Resolved). "
            f"Got {row['prior_pass_count']}."
        )

    def test_prior_followup_count(self, fm):
        row = self._get_row(fm)
        assert row["prior_followup_count"] == 3, (
            "Elevator 17489 had 3 prior Follow-Up outcomes before 2014-02-12: "
            "2013-10-24 (Follow up ×2) and 2014-01-29 (Follow up). "
            f"Got {row['prior_followup_count']}."
        )

    def test_prior_fail_count(self, fm):
        row = self._get_row(fm)
        assert row["prior_fail_count"] == 4, (
            "Elevator 17489 had 4 prior Fail/Shutdown outcomes before 2014-02-12: "
            "Shutdown on 2012-02-23, 2012-03-05, 2012-03-07, and 2012-03-08. "
            f"Got {row['prior_fail_count']}."
        )

    def test_total_prior_count_is_nine(self, fm):
        row = self._get_row(fm)
        total = row["prior_pass_count"] + row["prior_followup_count"] + row["prior_fail_count"]
        assert total == 9, (
            "Sum of prior pass+followup+fail counts for elevator 17489 on 2014-02-12 "
            "should be 9 (all 9 prior inspections fall into a known outcome class). "
            f"Got {total}. If total > 9, the current or future inspections are being "
            "counted; if total < 9, some prior inspections are being dropped."
        )


# ---------------------------------------------------------------------------
# Test 2 — An elevator's first-ever inspection must have zero (or NaN) for
#           all prior-inspection aggregate features.
# ---------------------------------------------------------------------------

class TestFirstInspectionHasZeroPriorFeatures:
    """
    Elevator 23920 appears exactly once in inspection.csv (date 2011-01-10).
    That record is by definition its first inspection; there is no prior
    history to aggregate, so every lookback feature must be 0 or NaN.
    """

    ELEV_ID = 23920
    TARGET_DATE = pd.Timestamp("2011-01-10")

    def _get_row(self, fm):
        mask = (
            (fm["ElevatingDevicesNumber"] == self.ELEV_ID)
            & (fm["Latest_INSPECTION_Date"] == self.TARGET_DATE)
        )
        rows = fm[mask]
        assert len(rows) == 1, (
            f"Expected exactly 1 feature-matrix row for elevator {self.ELEV_ID} "
            f"on {self.TARGET_DATE.date()}; found {len(rows)}"
        )
        return rows.iloc[0]

    def test_prior_pass_count_is_zero(self, fm):
        row = self._get_row(fm)
        assert row["prior_pass_count"] == 0, (
            f"prior_pass_count should be 0 for a first-ever inspection; "
            f"got {row['prior_pass_count']}"
        )

    def test_prior_followup_count_is_zero(self, fm):
        row = self._get_row(fm)
        assert row["prior_followup_count"] == 0, (
            f"prior_followup_count should be 0 for a first-ever inspection; "
            f"got {row['prior_followup_count']}"
        )

    def test_prior_fail_count_is_zero(self, fm):
        row = self._get_row(fm)
        assert row["prior_fail_count"] == 0, (
            f"prior_fail_count should be 0 for a first-ever inspection; "
            f"got {row['prior_fail_count']}"
        )

    def test_days_since_last_inspection_is_nan(self, fm):
        row = self._get_row(fm)
        assert math.isnan(row["days_since_last_inspection"]), (
            "days_since_last_inspection should be NaN for a first-ever inspection "
            "(no previous inspection exists to measure elapsed time from). "
            f"Got {row['days_since_last_inspection']}."
        )

    def test_prior_order_count_is_zero(self, fm):
        row = self._get_row(fm)
        assert row["prior_order_count"] == 0, (
            f"prior_order_count should be 0 for a first-ever inspection; "
            f"got {row['prior_order_count']}"
        )


# ---------------------------------------------------------------------------
# Test 3 — No order from an inspection dated on or after D may appear in the
#           order features for an inspection row with date D.
# ---------------------------------------------------------------------------

class TestNoFutureOrderDataInFeatures:
    """
    Elevator 17489, inspection date 2014-02-12.

    Orders linked to prior inspections (date < 2014-02-12): 15.
    Orders linked to current/future inspections (date >= 2014-02-12): 20.

    The feature matrix row must reflect exactly 15 prior orders.
    A prior_order_count of 35 would indicate future-order leakage (all orders
    pooled for the device before filtering by date).
    """

    ELEV_ID = 17489
    TARGET_DATE = pd.Timestamp("2014-02-12")

    EXPECTED_PRIOR_ORDER_COUNT = 15
    EXPECTED_FUTURE_ORDER_COUNT = 20

    def _get_row(self, fm):
        mask = (
            (fm["ElevatingDevicesNumber"] == self.ELEV_ID)
            & (fm["Latest_INSPECTION_Date"] == self.TARGET_DATE)
        )
        rows = fm[mask]
        assert len(rows) == 1
        return rows.iloc[0]

    def test_prior_order_count_excludes_future_orders(self, fm):
        row = self._get_row(fm)
        count = row["prior_order_count"]
        assert count == self.EXPECTED_PRIOR_ORDER_COUNT, (
            f"Elevator {self.ELEV_ID} on {self.TARGET_DATE.date()}: expected "
            f"{self.EXPECTED_PRIOR_ORDER_COUNT} prior orders (from 9 prior inspections). "
            f"Got {count}. "
            f"If count is {self.EXPECTED_PRIOR_ORDER_COUNT + self.EXPECTED_FUTURE_ORDER_COUNT}, "
            "future orders from the current and later inspections are leaking into the feature."
        )

    def test_raw_future_order_count_matches_expectation(self, raw_inspection, raw_orders):
        """
        Sanity-check the raw data: confirm it still contains the 20 future/current
        orders that should be excluded. If this assertion fails, the source data
        changed and the expected_prior_order_count above must be re-verified.
        """
        future_insp_nums = raw_inspection[
            (raw_inspection["ElevatingDevicesNumber"] == self.ELEV_ID)
            & (raw_inspection["Latest_INSPECTION_Date"] >= self.TARGET_DATE)
        ]["InspectionNumber"].tolist()

        future_order_count = len(
            raw_orders[raw_orders["inspectionnumber"].isin(future_insp_nums)]
        )
        assert future_order_count == self.EXPECTED_FUTURE_ORDER_COUNT, (
            f"Expected {self.EXPECTED_FUTURE_ORDER_COUNT} raw orders for current/future "
            f"inspections of elevator {self.ELEV_ID}; got {future_order_count}. "
            "The source data may have changed — re-verify EXPECTED_PRIOR_ORDER_COUNT."
        )

    def test_feature_order_count_differs_from_combined_total(self, fm):
        """
        Extra guard: the feature matrix count must not equal the combined total
        of prior + future orders, which would be the result of aggregating all
        orders for the device without any date filter.
        """
        row = self._get_row(fm)
        combined_total = self.EXPECTED_PRIOR_ORDER_COUNT + self.EXPECTED_FUTURE_ORDER_COUNT
        assert row["prior_order_count"] != combined_total, (
            f"prior_order_count equals {combined_total}, the combined count of prior AND "
            "future orders. This indicates the order filter is missing entirely."
        )
