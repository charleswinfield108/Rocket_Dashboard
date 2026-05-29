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
