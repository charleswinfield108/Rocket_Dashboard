# AND-104 Task 7: Fleet Health Feature

**Action:** Build fleet-level API endpoints using a repeatable development workflow skill

**Tools:** Claude Code, Go

**Spec Files Modified:** docs/api_spec.md (updated with two new endpoints)

---

## Detailed Requirements

The operations manager has seen the individual elevator endpoints and wants the big picture: fleet-level statistics and a list of elevators needing immediate attention.

### Development Workflow Skill

Create a development workflow skill at .claude/skills/new-endpoint/SKILL.md that defines a repeatable process for adding a new API endpoint:

- Set user-invocable: true in frontmatter
- The skill takes an endpoint name and description as arguments (e.g., /new-endpoint fleet-stats "Returns aggregate fleet statistics")
- Its instructions define a multi-step workflow covering spec update, code generation, route registration, and validation

### New Endpoints

Use /new-endpoint to build each of the following endpoints. The skill handles the full workflow (spec update, code, routing, validation). Provide the business requirements below as input:

**GET /api/fleet/stats**

- Returns aggregate fleet statistics
- Response includes: total elevator count, count per risk level (high, medium, low), overall inspection pass rate, count per equipment type

**GET /api/fleet/alerts**

- Returns elevators needing immediate attention: high risk score AND most recent inspection outcome is a failure
- Response is an array of elevator records with: elevator_id, risk_score, risk_level, last_inspection_date, last_inspection_outcome, equipment_type
- Sorted by risk score (highest first)

After the skill runs, review what it produced. Verify the spec entries are complete (JSON response shapes, error responses, examples), review the generated Go code, and confirm both endpoints pass /validate-api. The alerts endpoint requires joining data from multiple CSV sources (elevator data, inspections, and predictions).

### Custom CC Extension

After building both endpoints, reflect on friction you experienced during this task. Identify one new CC extension (a hook, skill, or subagent) that would have made the work smoother. Implement it, test it, and document in your AI Interaction Log what problem it solves and why you chose that extension mechanism.

Commit the new-endpoint skill, updated API spec, new Go handlers, and your custom CC extension.

---

## Deliverable

- .claude/skills/new-endpoint/SKILL.md
- Updated docs/api_spec.md
- New Go handlers in platform/api/
- One custom CC extension (hook, skill, or subagent)

---

## Evaluation Criteria

- Work starts with a markdown header identifying the task
- The new-endpoint skill sets user-invocable: true in frontmatter
- The new-endpoint skill defines a multi-step workflow (spec update, code generation, route registration, validation)
- API spec includes both new endpoints with fully specified JSON response shapes, error responses, and examples
- GET /api/fleet/stats returns correct aggregate statistics (total elevators, counts per risk level, pass rate, counts per equipment type)
- GET /api/fleet/alerts returns only elevators matching the alert criteria (high risk AND failed most recent inspection), or an empty array if no elevators match
- Alerts are sorted by risk score (highest first)
- Both endpoints use real data from CSV files (not hardcoded)
- A custom CC extension is implemented with documentation justifying the mechanism choice
- AI Interaction Log includes an entry about the custom CC extension and why that mechanism was chosen
- /validate-api confirms both new endpoints match the spec
