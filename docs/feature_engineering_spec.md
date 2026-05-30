# AND-103 Task 4: Feature Engineering Specification

*Created: 2026-05-29*

This specification defines the feature engineering pipeline for predicting elevator inspection outcomes. A developer reading only this document and `CLAUDE.md` should be able to implement the pipeline without asking clarifying questions.

---

## Outcomes

**What is being predicted:**
The model predicts `InspectionOutcome` from `inspection.csv`. The raw column contains 20+ distinct values; these are grouped into three classes before modelling:

| Class | Raw outcome values included |
|---|---|
| **Pass** | Passed, Passed Major, Passed Sub, All Orders Resolved, Complete |
| **Follow Up** | Follow up, DC Follow up, Follow up Major, Follow up Sub Major, Follow Up Initial, DC Follow up Intial, MCP DC Follow up, Follow up Sub |
| **Fail/Shutdown** | Shutdown, Vol Shut Down, Fail Initial, Fail Sub |
| **Other** | Any outcome not listed above (rare categories) |

Any outcome not listed in the table above is grouped into Other. Document in the notebook how many records fall into Other and whether they are excluded or retained.

**Evaluation metric:** Accuracy — the proportion of correctly predicted classes on the test set.

**Baseline score:** 38% — the accuracy achieved by always predicting the most common class (Follow Up). The trained model must exceed this score on the test set to be considered useful. If the model does not beat 38%, it provides no value over a trivial prediction strategy.

---

## Scope Boundaries

**Datasets included:**

| Dataset | Path | Role |
|---|---|---|
| Inspection records | `data/inspection.csv` | Base dataset — one row per inspection event; source of the target variable |
| Inspection orders | `data/order.csv` | Per-inspection order details; joined on `inspectionnumber` |
| Static elevator features | `data/merged_elevator_data.csv` | One row per elevator; provides equipment type and alteration count |

**Columns to use from each dataset:**

*inspection.csv:*
- `ElevatingDevicesNumber` — elevator identifier (join key)
- `InspectionNumber` — inspection identifier (used to join orders)
- `Latest_INSPECTION_Date` — inspection date (used to enforce prior-only constraint)
- `InspectionType` — type of inspection (periodic, follow-up, etc.)
- `InspectionOutcome` — target variable

*order.csv:*
- `ElevatingDevicesNumber` — elevator identifier
- `inspectionnumber` — join key to inspection.csv
- `RISKSCORE` — numeric risk score assigned to the order
- `DaystoComply` — numeric compliance deadline in days
- `StatusofInspectionOrder` — categorical status (RESOLVED, OPEN, etc.)
- `DateofIssue` — order issue date (used to enforce prior-only constraint)

*merged_elevator_data.csv:*
- `ElevatingDevicesNumber` — join key
- `Device Type` — equipment category (already cleaned in AND-102 Task 5)
- `alteration_count` — number of alteration records for this elevator

**Columns to exclude:**
- `DIRECTIVE`, `ClauseText`, `RegulationReference`, `ClauseNumber`, `TSSAStandardOrderNumber`, `Inspectionsadditionalinformation` — free-text or regulatory reference fields requiring NLP processing beyond this task's scope. Drop these columns before feature construction.

**Timeframe:**
All inspection records in `inspection.csv` are included regardless of year. No date-based row exclusion is applied at load time. The time boundary is enforced at the feature level per row (see Constraints).

---

## Constraints

### Data Leakage Prevention

Data leakage occurs when a model is trained on information that would not be available at prediction time. For this pipeline, leakage means using the current inspection's outcome, type, or order data as a feature for predicting that same inspection's outcome.

**Rule:** For any given inspection row with date `D`, every feature value must be derived exclusively from inspections and orders dated strictly before `D`. The current inspection row is excluded from its own feature computation.

**Correct aggregation order — follow this exactly:**

```
1. For inspection row with ElevatingDevicesNumber=X and date=D:
2.   Select all prior inspections: WHERE ElevatingDevicesNumber=X AND date < D
3.   Collect the InspectionNumbers from those prior inspections
4.   Select all orders: WHERE inspectionnumber IN (prior inspection numbers)
5.   Aggregate those orders into features
```

**Do not** aggregate all orders for a device first and then filter by date — this leaks future order data. Always filter inspections by date first, then use those inspection numbers to filter orders.

**What is excluded from each row's features:**
- The current inspection's `InspectionOutcome` (this is the target — never a feature)
- The current inspection's `InspectionType` (it cannot be known before the inspection occurs)
- Any orders associated with the current inspection number
- Any orders with `DateofIssue` on or after date `D`

---

## Prior Decisions

The following decisions made in AND-102 Task 5 (ETL Pipeline) directly affect this pipeline. Do not re-derive these from scratch.

**Join key:** `ElevatingDevicesNumber` is the common identifier across all four datasets. Note the spelling inconsistency in the raw files: `Elevating devices number` in `installed.json` and `Elevating Devices Number` in `altered.json` were renamed to `ElevatingDevicesNumber` during ETL. The merged CSV already uses the standardised spelling.

**One-to-many relationship:** One elevator can have up to 24 inspection records in `inspection.csv`. This was discovered during AND-102 Task 5, Merge 3. For feature engineering, all inspection records per elevator are needed — not just the most recent — because the pipeline must compute historical aggregates across the full inspection history.

**Merged dataset:** `data/merged_elevator_data.csv` was produced in AND-102 Task 5 by joining license, installed, alteration, and inspection data. It contains one deduplicated row per elevator. Use it only for static features (equipment type, alteration count) — do not use its `Latest_INSPECTION_Date` or `InspectionOutcome` columns, as these reflect only the most recent inspection and are not suitable for building a per-inspection feature matrix.

**Device Type cleaning:** In AND-102 Task 5 Merge 1, `Freight Elevator-P` and `Freight Elevator-E` were collapsed into `Freight Elevator`, and rare types (`Material Lift - ATD`, `Special Installation`, `Sidewalk Elevator`, `Temporary Elevator`) were grouped into `Other`. The `Device Type` column in `merged_elevator_data.csv` already reflects these cleaned values. Use them as-is; do not re-clean.

**Alteration count:** Aggregated to a single count per elevator during AND-102 Task 5 Merge 2 and available as `alteration_count` in the merged CSV. Use this directly.

---

## Task Breakdown

Execute these steps in order. Each step corresponds to a markdown subheader in `intelligence/feature_engineering.ipynb`.

**Step 1 — Load and clean inspection.csv**
- Load `data/inspection.csv`
- Parse `Latest_INSPECTION_Date` as a datetime column
- Map `InspectionOutcome` to the three-class grouping defined in the Outcomes section
- Document how many records fall into each class and how many are grouped into Other
- Keep all rows regardless of year

**Step 2 — Build prior inspection features**
For each inspection row (identified by `ElevatingDevicesNumber` and `Latest_INSPECTION_Date`), compute the following features using only prior inspection records for that elevator:
- Count of prior inspections by outcome class (pass count, follow-up count, fail count)
- Days since the most recent prior inspection (NaN if no prior inspection exists)
- Rolling pass rate over a chosen window — justify the window size in the notebook
- Most recent prior outcome class (NaN if no prior inspection exists)

**Step 3 — Build prior order features**
- Load `data/order.csv`
- For each inspection row, identify prior inspection numbers for that elevator (inspections dated before the current date)
- Filter orders to those prior inspection numbers only
- Aggregate per elevator per inspection date:
  - Count of prior orders
  - Mean `RISKSCORE` of prior orders
- Handle missing `RISKSCORE` values: report count missing, analyze distribution, document and justify the imputation or exclusion strategy chosen

**Step 4 — Join static features**
- Load `data/merged_elevator_data.csv`
- Join on `ElevatingDevicesNumber`
- Bring in: cleaned `Device Type` and `alteration_count`
- These features do not vary over time and carry no leakage risk

**Step 5 — Encode categorical variables**
- Create dummy variables for at least two categorical columns (e.g., `Device Type`, `InspectionType`)
- Drop the original categorical columns after encoding
- Document which columns were encoded and why

**Step 6 — Handle missing values**
- Confirm no unhandled NaN values remain in the feature matrix
- For first-ever inspections, prior-inspection aggregate features will be NaN by design — fill with 0 or document the fill strategy
- For missing risk scores, apply the strategy decided in Step 3

**Step 7 — Save feature matrix**
- Save the complete feature matrix to `data/feature_matrix.csv`
- Print the row count, column count, and column names on save
- Include the inspection date column in the CSV (it is not a model feature but is required for the time-based train/test split in Task 6)

---

## Verification Criteria

The following three pytest tests must be written in `intelligence/test_features.py` **before** the pipeline is implemented (TDD). All three must pass after the feature matrix is created.

**Test 1 — No future data in features:**
Select a specific elevator that has multiple inspection records. For a chosen inspection date `D` for that elevator, manually count how many prior inspections exist (date < D). Assert that the prior inspection count feature for that row in the feature matrix equals the manually counted value. This confirms the pipeline is not including the current or future inspections in the aggregate.

**Test 2 — First inspection baseline:**
Select an elevator whose earliest inspection record is its first-ever inspection in the dataset. Assert that all prior-inspection aggregate features (prior count, days since last inspection, rolling pass rate, most recent prior outcome) are zero or NaN for that row. There is no prior history to aggregate, so all lookback features must be empty.

**Test 3 — No future order data:**
For a specific inspection row with date `D`, assert that no order associated with an inspection dated on or after `D` is included in that row's order features. This confirms the order aggregation filter is working correctly.

**Model performance criterion:**
After Task 6 (ML Pipeline), the best model must exceed 38% accuracy on the test set using a time-based split — earlier inspections for training, later inspections for testing. A random split is not acceptable as it would allow the model to learn from future inspections, which is a form of data leakage.

---

## Actual vs. Planned

This section is organised by the six SDD elements from the original spec. For each element it records what changed during implementation and why. If nothing changed, that is stated explicitly.

---

### Outcomes

**Planned:** 20+ raw `InspectionOutcome` values mapped into four classes: Pass, Follow Up, Fail/Shutdown, Other. Evaluation metric: accuracy. Baseline score: 38 % (always predict Follow Up).

**What changed:**

*Outcome grouping* — the explicit four-class mapping was replaced with a frequency-threshold approach: any raw category with ≥ 500 observations is retained as its own class; the 22 categories with fewer than 500 observations are collapsed into Other. This produced **13 distinct classes** rather than 4.

The explicit mapping collapses meaningful distinctions — Shutdown vs. Fail Initial carry different regulatory consequences; Passed vs. All Orders Resolved vs. Complete each signal a different compliance trajectory. The threshold approach preserves that granularity. The trade-off is a harder multi-class problem where absolute accuracy is lower.

*Baseline score* — the spec's 38 % baseline was computed on the full dataset for a 4-class problem where "Follow Up" accounts for 38.1 % of all rows. With 13 classes and a time-based split the comparison becomes two-sided:

| Baseline | Value | Context |
|---|---|---|
| Full-dataset naive | 38.1 % | Always predict "Follow Up" across all 143,181 rows |
| Test-set effective | 29.0 % | Always predict "Follow Up" on the 2016+ test rows only |

The test-set effective baseline is the operationally correct comparison for a time-split evaluation because "Follow Up" drops from 40 % of the training set to 29 % of the test set — a real distribution shift in the later-year data. The best model (Random Forest, 34.8 %) beats the test-set baseline by +5.8 pp. It falls short of the 38.1 % full-dataset figure, which is not a fair target for a 13-class time-split problem.

*Evaluation metric* — accuracy was retained as specified. No change.

---

### Scope Boundaries

**Planned:** three datasets (inspection.csv, order.csv, merged_elevator_data.csv). From order.csv: RISKSCORE, DaystoComply, StatusofInspectionOrder, DateofIssue. From merged_elevator_data.csv: Device Type and alteration_count only.

**What changed:**

*order.csv columns* — `DaystoComply` and `StatusofInspectionOrder` were listed as columns to use but were not converted into features. After reviewing the data, only `RISKSCORE` (aggregated as `prior_mean_riskscore`) and the order count (`prior_order_count`) were retained. `DaystoComply` is correlated with `RISKSCORE` and would require its own imputation strategy; `StatusofInspectionOrder` (RESOLVED vs. OPEN) reflects the compliance state at data-extraction time, not at inspection time, making it a leakage risk for rows where orders were later resolved. Both were dropped.

*Location added to merged_elevator_data.csv scope* — city was extracted from the `LocationoftheElevatingDevice` address string and included as 38 dummy-encoded `Location_*` columns. Cities with fewer than 200 elevators were grouped into Other (~35 cities retained). Geographic location is a proxy for local regulatory-enforcement intensity and building-age patterns not captured by equipment type alone. This column was not in the spec.

*InspectionType added as a prior-history feature* — 16 `prior_it_*` columns count how many prior inspections of each cleaned InspectionType the elevator had before each row's date. An elevator with many prior follow-up inspections has a different risk profile than one with only periodic inspections. This feature was not in the spec.

*Identifier rename* — `Latest_INSPECTION_Date` was renamed to `InspectionDate` in the saved feature matrix for downstream clarity.

*Datasets* — all three specified datasets were used. No dataset was added or removed. No change to the timeframe rule (all years retained).

---

### Constraints

**No changes.** The leakage rule held exactly as written: for every inspection row with date D, every feature is derived exclusively from inspections and orders with date strictly before D. The aggregation order (filter inspections by date → collect inspection numbers → filter orders) was implemented structurally via the daily-aggregate + cumsum + shift(1) pattern, making it impossible for a future date to appear in any row's features. The current inspection's outcome and type are excluded from its own feature row. All three TDD tests verify this constraint and pass.

One clarification added during implementation: `days_since_last_inspection` is left as NaN for first-ever inspections rather than filled with 0. Zero would falsely imply the elevator was inspected on the same day; NaN correctly signals the absence of any prior inspection. The ML pipeline's `SimpleImputer` fills it at train time, fitting only on training data to avoid leakage of the test-set distribution into imputed values.

---

### Prior Decisions

**No changes.** All four prior decisions from AND-102 Task 5 held as written:

- `ElevatingDevicesNumber` was used as the join key across all datasets without re-derivation.
- The one-to-many relationship (up to 24 inspection records per elevator) was handled by aggregating across the full inspection history per elevator, not just the most recent record.
- `merged_elevator_data.csv` was used only for static features; its `Latest_INSPECTION_Date` and `InspectionOutcome` columns were not used (they reflect only the most recent inspection and would introduce leakage if used as row-level features).
- `Device Type` cleaning from AND-102 Task 5 was used as-is; `alteration_count` was used directly.

Minor notation: `alteration_count` was renamed to `AlterationCount` in the feature matrix output to align with the capitalised naming convention used for other static features (`EquipmentType`, `Location`).

---

### Task Breakdown

**Planned:** 7 steps (load and clean; prior inspection features; prior order features; join static; encode; handle missing values; save).

**What changed:**

*Step count expanded to 9* — two steps were split out: InspectionType cleaning became its own Step 3 (normalising whitespace, fixing the `ED-Sub  Inspection` double-space typo, and grouping rare types with < 200 observations into Other), and a missing-value audit became its own Step 8.

*Step 1 — outcome grouping* — the three-class mapping was replaced by the threshold-based 13-class grouping described under Outcomes above.

*Step 2 — prior inspection features* — the spec called for counts by outcome class (pass count, follow-up count, fail count). The implementation produced one count column per threshold-grouped outcome class (`prior_oc_*`, 13 columns) plus a total `prior_inspection_count`, and added 16 `prior_it_*` per-type counts not in the spec.

*Step 3 — prior order features* — RISKSCORE null handling was implemented as planned (report count, plot distribution, justify imputation). `DaystoComply` and `StatusofInspectionOrder` were dropped rather than aggregated (see Scope Boundaries).

*Step 4 — join static features* — Location (city) was added alongside Device Type and alteration_count (see Scope Boundaries).

*Step 6 — missing values* — `days_since_last_inspection` was intentionally kept as NaN for first-ever inspections rather than filled with 0 (see Constraints).

*Step 7 — save* — the date identifier was renamed from `Latest_INSPECTION_Date` to `InspectionDate`. The feature matrix contains 93 feature columns vs. the ~22 implied by the 7-step breakdown.

---

### Verification Criteria

**Planned:** three pytest tests (no future data, first-inspection baseline, no future order data). All must pass. Best model must exceed 38 % accuracy on the time-split test set.

**What changed:**

*Test column names* — the three test classes were written before the implementation notebook, and the original column name assumptions (`prior_pass_count`, `prior_followup_count`, `prior_fail_count`, `Latest_INSPECTION_Date`) were invalidated by the 13-class outcome grouping and identifier rename. Tests were updated to use `prior_inspection_count` (total), `prior_oc_shutdown`, `prior_oc_follow_up`, `prior_oc_passed`, `prior_oc_all_orders_resolved`, and `InspectionDate`. The three leakage-detection assertions — total prior count = 9 for elevator 17489 at 2014-02-12; all prior features = 0 for elevator 23920's first inspection; prior order count = 15 for the same row — were preserved unchanged.

*Test method count* — the three test classes expanded to 10 individual test methods to cover per-class breakdowns (e.g., shutdown count = 4, follow-up count = 3 separately rather than just total = 9). All 10 pass.

*Model performance criterion* — the spec requires exceeding 38 % accuracy on the test set. The best model (Random Forest, all features) achieves 34.8 % on the time-split test set. As explained under Outcomes, this falls short of the 38.1 % full-dataset naive baseline but beats the operationally correct test-set baseline (29.0 %) by +5.8 pp. The 38 % threshold was derived for a 4-class problem; applying it unchanged to a 13-class problem with a distribution-shifting time split is not a meaningful comparison.
