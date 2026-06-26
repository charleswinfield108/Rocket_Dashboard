# AND-104 Task 2: API Specification

**Action:** Write a REST API specification for the Go backend service using the six SDD elements

**Tools:** Claude Code

**Spec Files Modified:** docs/api_spec.md (new file)

---

## Detailed Requirements

Create docs/api_spec.md. Structure the specification using the six SDD elements from Module 3 (outcomes, scope boundaries, constraints/assumptions, prior decisions, task breakdown, verification criteria). This API is a pure JSON service; it does not serve HTML.

Based on the business needs and the data available in your CSV files, define these endpoints:

- `GET /api/elevators` — list the elevator fleet
- `GET /api/elevators/{id}` — full details for a single elevator
- `GET /api/elevators/{id}/inspections` — inspection history for a specific elevator
- `GET /api/elevators/{id}/risk` — predicted risk for a specific elevator

For each endpoint, determine which fields to include in the JSON response by examining your actual CSV data. Define error responses for each endpoint (what happens when a resource is not found, when parameters are invalid).

Write example responses for each endpoint using realistic data from your datasets.

Define the data sources: which CSV files the Go server reads and how they map to response fields. Note that data/predictions.csv does not exist yet; it will be generated in Task 6. Your spec should define the risk endpoint's expected response shape now and note this forward dependency.

Commit the spec.

---

## Deliverable

- docs/api_spec.md

---

## Evaluation Criteria

- Work starts with a markdown header identifying the task
- The spec is structured using the six SDD elements (outcomes, scope boundaries, constraints/assumptions, prior decisions, task breakdown, verification criteria)
- All four endpoints are defined with HTTP method, path, and description
- JSON response shapes are fully specified with field names and types derived from the actual CSV data
- Error responses are defined for each endpoint
- Example responses use realistic data consistent with the existing datasets
- Data source mapping explains which CSV files supply which response fields, including the forward dependency on data/predictions.csv
- The spec is detailed enough that another developer could implement the API without clarifying questions
