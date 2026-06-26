# AND-104 Task 8: Dashboard Integration and Verification

**Action:** Integrate all API data into the dashboard and verify the end-to-end system

**Tools:** Claude Code, Python, HTMX, validate-api skill

**Spec Files Modified:** N/A

---

## Detailed Requirements

Use the /validate-api skill to verify all six API endpoints against the spec. Document any mismatches and fix them.

### Frontend Updates

Update the Python/HTMX frontend to display:

- **Risk badges in the fleet table:** a color-coded indicator for each elevator (red for high, yellow for medium, green for low risk)
- **Risk score and prediction date in the elevator detail panel**
- **A fleet health panel** showing summary statistics from /api/fleet/stats (total elevators, risk level distribution, inspection pass rate)
- **An alerts section** listing elevators flagged by /api/fleet/alerts

All data displayed on the dashboard must come from the Go API (not read directly from CSV files by the frontend).

### End-to-End Verification

- Start both servers (Python frontend and Go API)
- Navigate the dashboard: risk badges appear in the fleet table
- Click an elevator: detail panel shows risk score and prediction date from the API
- Fleet health panel displays correct aggregate statistics
- Alerts section displays results from the alerts endpoint
- Confirm the full data pipeline: feature matrix (M3) -> predictions (Task 6) -> Go API -> dashboard

### Hooks Refinement

Review your hooks configuration from Task 4. Based on your experience across Tasks 4-7, refine at least one existing hook to handle a case it did not cover originally. Document the refinement and what motivated it in your AI Interaction Log.

### CC Extensions Reflection

Assess the CC extensions you built across this module (hooks, skills, subagent). In your AI Interaction Log, write one entry reflecting on which extension delivered the most value and one that you would design differently if starting over. Reference specific moments from your work.

Commit the frontend updates, refined hooks, and updated log.

---

## Deliverable

- Updated dashboard displaying risk indicators, fleet health statistics, and alerts
- All API endpoints validated
- Refined hooks configuration

---

## Evaluation Criteria

- Work starts with a markdown header identifying the task
- All six API endpoints pass validation against docs/api_spec.md
- Risk badges appear in the fleet table with color coding (red/yellow/green)
- The detail panel displays risk score and prediction date
- Fleet health panel shows aggregate statistics from the stats endpoint
- Alerts section displays flagged elevators from the alerts endpoint
- All data is sourced from the Go API (not direct CSV reads from the frontend)
- Both servers run simultaneously and the dashboard is fully functional
- At least one existing hook is refined with a documented reason for the change
- AI Interaction Log includes a reflection entry assessing which CC extensions worked well and what the student would change
