# AND-104 Task 5: Full-Stack Integration with Validation Tooling

**Action:** Build validation tooling for your API and connect the Python/HTMX frontend to the Go API

**Tools:** Claude Code, Python, HTMX

**Spec Files Modified:** N/A

---

## Detailed Requirements

The learning cards explain the difference between skills and subagents. Read those before starting this task.

Before wiring the integration, create tooling to validate your API endpoints against the spec. You will use this tooling throughout the rest of the module as you add endpoints and integrate data.

### Custom subagent: api-validator

Create .claude/agents/api-validator.md with a role description and structured workflow. This subagent validates an API endpoint against your specification in docs/api_spec.md. It should test a live endpoint, compare the response to what the spec defines, and report whether the endpoint conforms with enough detail to identify what is wrong if it does not.

### Action skill: validate-api

Create a user-invocable skill at .claude/skills/validate-api/SKILL.md that takes an endpoint path as an argument (e.g., /validate-api /api/elevators) and delegates the validation work to the api-validator subagent.

Run /validate-api on each of the four endpoints to verify they match your spec before starting integration work.

### Frontend Integration

Update the Python frontend to call the Go API for data that the API now owns:

- The elevator detail panel (from Module 3) should fetch data from the Go API's /api/elevators/{id} endpoint instead of reading CSVs directly
- Risk scores (once available from Task 6) should come from the Go API's /api/elevators/{id}/risk endpoint

Choose an integration strategy (server-side proxy or direct client-side calls) and implement it. Document which option you chose and why in your AI Interaction Log.

Handle the case where the Go API is unavailable: the frontend should show a clear error state, not crash.

### Verification

- Start both servers
- Navigate the dashboard and confirm the detail panel still works
- Confirm data shown in the frontend matches what the Go API returns

Commit the validation tooling and integration changes.

---

## Deliverable

- .claude/agents/api-validator.md
- .claude/skills/validate-api/SKILL.md
- Updated Python frontend calling the Go API

---

## Evaluation Criteria

- Work starts with a markdown header identifying the task
- Api-validator subagent has a role description, a defined workflow, and a structured output format
- Api-validator subagent checks enough dimensions to catch a meaningful mismatch between spec and implementation
- Validate-api skill sets user-invocable: true in frontmatter
- Validate-api skill references the api-validator subagent in its instructions
- All four endpoints pass validation via /validate-api
- The Python frontend fetches at least one data type from the Go API instead of reading CSVs directly
- Both servers can run simultaneously without port conflicts
- The dashboard remains fully functional with the Go API running
- The frontend handles API unavailability gracefully (error message, not crash)
- AI Interaction Log includes an entry documenting the integration strategy choice
- The detail panel displays correct data sourced from the Go API
