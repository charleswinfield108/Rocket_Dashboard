# AND-103 Methodology Report

*Charles Winfield — 2026-05-29*

---

## 1. Feature Engineering Summary

Features were built from three source datasets, all joined on `ElevatingDevicesNumber`.

**`inspection.csv` (143,181 rows — base table, source of the target variable)**

For each inspection row, prior-only history features were computed using every earlier inspection for the same elevator (date strictly less than the row's own `InspectionDate`):

- `prior_inspection_count` — total prior inspections
- `prior_oc_*` — 13 columns counting prior inspections in each outcome class (threshold-grouped: raw categories with ≥ 500 observations kept separately; the rest collapsed into Other)
- `prior_it_*` — 16 columns counting prior inspections of each cleaned InspectionType
- `days_since_last_inspection` — calendar days to the most recent prior inspection (NaN for first-ever inspections — intentionally not filled; 0 would imply a same-day inspection)
- `rolling_pass_rate` — fraction of prior inspections with a pass-like outcome (expanding window)
- `prior_outcome_*` — 14 dummy columns encoding the most recent prior outcome class

**`order.csv` (162,172 rows — compliance orders)**

Orders were tagged with their parent inspection's date, then prior-only aggregates were computed identically to the inspection features:

- `prior_order_count` — total orders from prior inspections
- `prior_mean_riskscore` — median-imputed, cumulative-weighted mean RISKSCORE across prior orders (25.6% of RISKSCORE values were null; global median of 15.0 used for imputation)

**`merged_elevator_data.csv` (43,251 rows — static elevator attributes)**

Joined once per elevator; carries no leakage risk because the values do not vary over time:

- `EquipmentType_*` — 6 dummy columns for equipment category
- `Location_*` — 38 dummy columns for city extracted from the address string (cities with fewer than 200 elevators grouped into Other)
- `AlterationCount` — number of recorded alterations

**Final feature matrix:** 143,181 rows × 93 feature columns (plus `InspectionDate` and `ElevatingDevicesNumber` as identifiers, and `outcome_class` as target).

**Leakage prevention:** the pipeline uses a daily-aggregate + cumsum + shift(1) pattern. Inspection rows are grouped by (elevator, date) to form one summary row per elevator-day, cumulative sums are computed within each elevator group, and `shift(1)` moves each total one date backwards — so every row's features reflect only dates strictly before its own. Multiple inspections on the same date are handled atomically because they share a single aggregate row. In the ML pipeline, `SimpleImputer` fits on training data only, so no test-set statistics leak into imputed values.

---

## 2. TDD Experience

Three test classes were written in `intelligence/test_features.py` and committed before any pipeline code existed:

| Test class | What it asserts |
|---|---|
| `TestNoPriorFeatureUsesCurrentOrFutureInspection` | Elevator 17489 at 2014-02-12: `prior_inspection_count` = 9, `prior_oc_shutdown` = 4, `prior_oc_follow_up` = 3 — all manually verified against raw CSV before any code was written |
| `TestFirstInspectionHasZeroPriorFeatures` | Elevator 23920 (only one inspection in the dataset): all prior counts = 0, `days_since_last_inspection` = NaN, `prior_order_count` = 0 |
| `TestNoFutureOrderDataInFeatures` | Elevator 17489 at 2014-02-12: `prior_order_count` = 15, not 35 — confirming the 20 orders from current and future inspections are excluded |

All 10 test methods failed with `FileNotFoundError` until the notebook produced the feature matrix, then passed immediately on the first successful execution.

**Issues caught:** the manual count required before writing Test 1 revealed that "All Orders Resolved" and "Passed" are two separate outcome classes in the threshold-grouped schema, contributing `prior_oc_all_orders_resolved` = 1 and `prior_oc_passed` = 1 independently. Without the count, a bug that collapsed them into a single column would have passed silently. When the notebook was later rebuilt with the 13-class schema, the column name changes surfaced immediately as test failures — the tests acted as a regression harness for the refactor, flagging exactly which assertions needed updating rather than requiring a full audit of the output.

**Workflow effect:** writing tests first made the feature specification concrete before implementation began. The test file defined the exact column names, the exact elevator/date pairs to verify, and the exact expected values — decisions that would otherwise have drifted during implementation.

---

## 3. Model Results

**Baseline:** always predict "Follow up" (the most common class, 38.1% of all rows). On the time-split test set specifically, "Follow up" accounts for only 29.0% of rows — the operationally correct floor any model must beat.

**Split:** time-based 80/20 split on `InspectionDate`. Cutoff: 2015-12-16. Train: 114,544 rows; test: 28,637 rows.

**Comparison:**

| Model | Score before feature selection | Score after feature selection (SelectKBest, k=30) |
|---|---|---|
| Logistic Regression | 32.0% | 31.0% |
| Random Forest | **34.8%** | 33.6% |

Metric: accuracy on the test set. Feature selection used `SelectKBest(mutual_info_classif, k=30)`, retaining the 30 features with the highest mutual information with the target.

**Best model: Random Forest with all 93 features, 34.8% accuracy** — +5.8 percentage points above the 29.0% test-set baseline.

Random Forest outperformed Logistic Regression because the relationships between prior-history counts and outcomes are non-linear. An elevator with five prior shutdowns is qualitatively more at risk than one with one; decision trees express this as explicit splits (`prior_oc_shutdown > 2`) that Logistic Regression can only approximate with smooth linear weights.

Feature selection reduced accuracy for both models. `mutual_info_classif` scores each feature independently, so it cannot see that the 13 `prior_oc_*` columns and 16 `prior_it_*` columns each contribute jointly to describe the full prior-history distribution. Dropping any single column looks cheap; dropping 63 together removes the joint signal.

---

## 4. Lessons Learned

**Spec:** the outcome grouping should have been decided in the spec, not during implementation. The original spec defined a fixed four-class mapping (Pass / Follow Up / Fail / Other) without stating why those four groups were chosen. During implementation the mapping was replaced with a data-driven threshold (≥ 500 observations), producing 13 classes. This changed the difficulty of the problem, invalidated the 38% baseline, and required rewriting the TDD tests. In future, the spec should commit to a grouping with explicit reasoning — for example: "Shutdown, Vol Shut Down, Fail Initial, and Fail Sub are merged into one class because the model should treat any forced-stop outcome equivalently" — so the implementation cannot silently reopen the decision.

**Pipeline:** `SelectKBest` was the wrong feature selection method for this feature set. Because `mutual_info_classif` scores each feature individually, it cannot represent the fact that removing several complementary `prior_oc_*` or `prior_it_*` columns together degrades performance far more than removing any single one. In future, a wrapper method — such as computing permutation importance on a fitted Random Forest and dropping the lowest-importance features — would select based on joint predictive contribution rather than marginal scores, and would likely retain the prior-history count columns while removing the sparse city dummies that carry weak signal.
