# AND-104 Task 3: Go API Implementation

**Action:** Initialize a Go project and implement the API endpoints from your specification

**Tools:** Claude Code, Go

**Spec Files Modified:** N/A

---

## Detailed Requirements

Create a platform/api/ directory for the Go service. Initialize a Go module (go mod init).

Implement the HTTP server with routing for all four endpoints defined in docs/api_spec.md. Use the standard library (net/http) or a lightweight router (e.g., chi, gorilla/mux). The server should:

- Listen on a configurable port (default 8081)
- Read data from your existing CSV files (data/merged_elevator_data.csv, data/inspection.csv, and later data/predictions.csv)
- Return JSON responses matching your API spec exactly

Verify the server runs and responds to requests. Test each endpoint with curl or a similar tool.

Commit the Go project.

---

## Deliverable

- Go API server in platform/api/ with all four endpoints implemented

---

## Evaluation Criteria

- Work starts with a markdown header identifying the task
- Go module initializes cleanly (go build succeeds without errors)
- All four endpoints return JSON responses matching the API spec
- Responses use real data from CSV files (not hardcoded mock data)
- GET /api/elevators returns the full fleet with all specified fields
- GET /api/elevators/{id} returns 404 for non-existent IDs
- GET /api/elevators/{id}/inspections returns records sorted by date (most recent first)
- GET /api/elevators/{id}/risk returns a placeholder or error until Task 6 populates predictions
- HTTP status codes and Content-Type headers are correct
- Code compiles and server starts without errors
