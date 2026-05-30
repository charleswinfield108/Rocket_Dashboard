# AND-103 Methodology Report

*Charles Winfield — 2026-05-29*

---

## 1. Feature Engineering Summary

### Source datasets and joins

| Dataset | Role | Join key |
|---|---|---|
| `inspection.csv` (143,181 rows) | Base table — one row per inspection event; source of the target variable | `ElevatingDevicesNumber` |
| `order.csv` (162,172 rows) | Per-inspection compliance orders; contributes prior order count and mean risk score | `inspectionnumber` |
| `merged_elevator_data.csv` (43,251 rows) | One row per elevator; contributes equipment type, location, alteration count | `ElevatingDevicesNumber` |

### Features created

**Prior inspection features (per elevator, strictly before each inspection date):**
- `prior_inspection_count` — total prior inspections
- `prior_oc_*` — 13 columns, one per outcome class (threshold-grouped); counts prior inspections in each class
- `prior_it_*` — 16 columns, one per cleaned InspectionType; counts prior inspections of each type
- `days_since_last_inspection` — calendar days between the current inspection and the most recent prior one (NaN for first-ever inspections)
- `rolling_pass_rate` — prior pass-like outcomes / total prior inspections (expanding window)
- `prior_outcome_*` — 14 dummy columns encoding the most recent prior outcome class

**Prior order features (linked to prior inspection numbers only):**
- `prior_order_count` — total orders from prior inspections
- `prior_mean_riskscore` — imputed-median-weighted mean risk score across prior orders

**Static features (joined from merged_elevator_data.csv):**
- `EquipmentType_*` — 6 dummy columns for equipment category
- `Location_*` — 38 dummy columns for city extracted from address string
- `AlterationCount` — number of alteration records on file

Final feature matrix: **143,181 rows × 96 columns** (93 features + InspectionDate + ElevatingDevicesNumber + outcome_class target).

### Data leakage prevention

For any inspection row with date D, every feature value is derived exclusively from
inspections and orders with dates strictly before D. The implementation uses a
**daily-aggregate + cumsum + shift(1)** pattern: inspections are grouped by
(elevator, date), cumulative sums are computed within each elevator group, and
`shift(1)` moves the running total one date backwards — so each row's features reflect
only prior dates. Multiple inspections on the same date are handled atomically because
they share a single aggregate row. The `SimpleImputer` in the ML pipeline fits only on
training data, preventing test-set distribution from leaking into imputed values.

---

## 2. TDD Experience

### Tests written

Three test classes in `intelligence/test_features.py` (10 methods total):

| Test | What it checks |
|---|---|
| `TestNoPriorFeatureUsesCurrentOrFutureInspection` | Elevator 17489 @ 2014-02-12: `prior_inspection_count` = 9 (manually counted), `prior_oc_shutdown` = 4, `prior_oc_follow_up` = 3 |
| `TestFirstInspectionHasZeroPriorFeatures` | Elevator 23920 (exactly 1 inspection in dataset): all prior counts = 0, `days_since_last_inspection` = NaN, `prior_order_count` = 0 |
| `TestNoFutureOrderDataInFeatures` | Elevator 17489 @ 2014-02-12: `prior_order_count` = 15 (not 35 — the leakage total) |

All 10 tests were committed before any pipeline code was written (`b237fde`). They
failed with `FileNotFoundError` until the feature matrix was produced, then passed
immediately on the first successful notebook execution.

### Effect on workflow

Writing tests first required manually counting prior inspections from raw CSV before
any code was touched. This process caught a subtle issue early: "All Orders Resolved"
and "Passed" are two separate outcome classes in the threshold-grouped schema, so
`prior_oc_passed` = 1 and `prior_oc_all_orders_resolved` = 1 — not 2 in a single
column. Without the manual count, this distinction would have been invisible until a
much later debugging session.

The tests also acted as a specification for column names. When the notebook was rebuilt
with a 13-class outcome schema, the column name changes were immediately surfaced as
test failures, guiding the exact updates needed in the test file.

---

## 3. Model Results

### Train / test split

| | Value |
|---|---|
| Method | Time-based (80/20 by inspection date) |
| Cutoff date | 2015-12-16 |
| Training rows | 114,544 (2011-01-04 – 2015-12-16) |
| Test rows | 28,637 (2015-12-16 – 2017-01-09) |

### Baseline

| Baseline | Value |
|---|---|
| Full-dataset naive (always predict "Follow up") | 38.1 % |
| Time-split test set (predict train's most common class on test) | **29.0 %** |

The time-split baseline (29.0 %) is the operationally correct comparison: the test set
covers 2016 inspections where "Follow up" accounts for only 29 % of outcomes, versus
40 % in the training set. Any model must beat 29.0 % to provide value.

### Model comparison

| Model | Features | Test accuracy | vs test baseline |
|---|---|---|---|
| Logistic Regression | All 93 | 32.0 % | +3.0 pp |
| Logistic Regression | Top 30 (SelectKBest) | 31.0 % | +2.0 pp |
| Random Forest | All 93 | **34.8 %** | **+5.8 pp** |
| Random Forest | Top 30 (SelectKBest) | 33.7 % | +4.7 pp |

Evaluation metric: **accuracy** (proportion of correctly classified outcomes on the
test set). All four models beat the 29.0 % baseline.

### Best model

**Random Forest with all 93 features — 34.8 % accuracy.**

Feature selection (SelectKBest, k=30) reduced performance slightly for both models: −1.0 pp for Logistic Regression and −1.1 pp for Random Forest. The top-30 selection favoured continuous prior-history counts (`prior_inspection_count`, `days_since_last_inspection`, `rolling_pass_rate`) and dropped most sparse city and outcome dummy columns — suggesting the dummies carry some signal even below SelectKBest's threshold.

Random Forest outperformed Logistic Regression because the relationships between
inspection history and outcomes are non-linear: an elevator with 10 prior "Follow up"
inspections is not simply 10× as likely to fail as one with 1. Tree-based splits capture
these threshold effects naturally.

Note: the original spec required exceeding 38 % accuracy. That threshold was computed
for a 4-class problem on the full dataset. With 13 classes and a time-based split,
34.8 % (beating a 29 % baseline) is the appropriate comparison — see Actual vs. Planned
in `docs/feature_engineering_spec.md` for the full explanation.

---

## 4. Lessons Learned

### What I would do differently about the spec

The original spec defined a fixed 4-class outcome mapping (Pass / Follow Up / Fail /
Other) without reasoning about why those four groups. The implementation replaced this
with a threshold-based grouping that produced 13 classes — a better reflection of the
data, but one that made the classification harder and invalidated the 38 % baseline.

**The fix:** include a "class grouping rationale" section in the spec that explicitly
argues for or against collapsing categories. A sentence like "We merge Shutdown, Vol
Shut Down, Fail Initial, and Fail Sub into one class because the model should treat
any shutdown equivalently" commits to a decision and makes the trade-off visible before
implementation begins.

### What I would do differently about the pipeline

Feature selection (SelectKBest) hurt performance in this pipeline because `f_classif`
scores features independently — it cannot capture interaction effects between the 13
`prior_oc_*` columns (which together describe the outcome history distribution) or
between the 16 `prior_it_*` type-count columns. Dropping any one feature looks
harmless in isolation; dropping 63 of them together removes the joint distribution.

**The fix:** use a wrapper method (e.g. `SequentialFeatureSelector` or permutation
importance from a fitted Random Forest) for feature selection instead of a filter
method. This would select features based on their combined predictive contribution
rather than marginal ANOVA scores, and would likely retain the complementary set of
prior outcome counts rather than redundant city dummies.
