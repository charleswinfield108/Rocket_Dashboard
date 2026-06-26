# AND-104 Task 6: Pre-Compute and Serve Predictions

**Action:** Generate risk predictions for all elevators and serve them through the Go API

**Tools:** Claude Code, Jupyter Notebook, Go

**Spec Files Modified:** N/A

---

## Detailed Requirements

In intelligence/generate_predictions.ipynb, load your Module 3 feature matrix (data/feature_matrix.csv) and re-train your best model using the model type and parameters from your Module 3 methodology report. Generate a risk score for every unique elevator in the fleet:

- For each elevator, use its most recent row in the feature matrix (the latest inspection features)
- Calculate a risk score using predict_proba (probability of follow-up inspection)
- Assign a risk level: high (score >= 0.7), medium (0.4 <= score < 0.7), low (score < 0.4)

### Validation

Validate the output before saving:

- All unique elevators from the feature matrix are represented (no missing IDs)
- All risk scores are in the range [0, 1]
- The risk level distribution is reasonable (not all one category)
- Print a summary: total elevators, count per risk level, min/max/mean risk score

Save the predictions to data/predictions.csv with columns: elevator_id, risk_score, risk_level, model_version (use a version string like "v4.1"), prediction_date.

### Go API Updates

Update the Go API's /api/elevators/{id}/risk endpoint to read from data/predictions.csv and return the prediction for the requested elevator. The Go server should load the predictions file into memory at startup for efficient lookups. The response must match the shape defined in docs/api_spec.md.

Update the Go API's /api/elevators list endpoint to include a risk_level field for each elevator (joining predictions data).

### Verification with /validate-api

- /api/elevators/{id}/risk returns a valid prediction for a known elevator
- /api/elevators/{id}/risk returns 404 for an elevator with no prediction
- /api/elevators list includes risk_level for elevators that have predictions

### Skill Update

Update your platform conventions skill (.claude/skills/platform-conventions/SKILL.md) with a convention for generated data files: data/predictions.csv is a generated artifact that should be regenerated from the notebook, not edited manually.

Commit the prediction notebook, predictions CSV, updated Go handlers, and updated skill.

---

## Deliverable

- intelligence/generate_predictions.ipynb
- data/predictions.csv
- Updated Go API serving predictions
- Updated .claude/skills/platform-conventions/SKILL.md

---

## Evaluation Criteria

- Work starts with a markdown header identifying the task
- Predictions cover all unique elevators in the feature matrix (no missing IDs)
- Predictions CSV contains all expected columns (elevator_id, risk_score, risk_level, model_version, prediction_date)
- Risk levels are correctly assigned based on score thresholds
- The notebook includes a validation summary (total elevators, count per risk level, score range)
- The /api/elevators/{id}/risk endpoint returns predictions matching the API spec
- The /api/elevators endpoint includes risk_level in its response
- 404 is returned for elevators without predictions
- The Go server loads predictions into memory at startup
- Platform conventions skill includes a convention about generated data files
- The notebook runs top-to-bottom without errors (Restart Kernel and Run All)
