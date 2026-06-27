# Additional Chatbot Queries — AND-107

Beyond the five required queries, the following queries have been identified and implemented as validated MCP tools backed by parameterized SQL. Each is available in `platform/mcp/tools/additional.py`.

---

## Query 6: "Which elevators have licences expiring in the next 90 days?"

**Tool:** `list_expiring_licences(days=90)`
**Source:** `elevators`

Licence expiry is a hard compliance deadline. If a licence lapses, the elevator must be taken out of service immediately — tenant disruption, potential fines, and an emergency re-licensing process follow. An operations manager running a building portfolio needs advance warning to start renewal paperwork before the expiry date, not after. The `days` window is configurable (default 90, max 3650) so the team can look further ahead during annual planning cycles.

```sql
SELECT id, location, device_type, license_status, license_expiry, license_holder
FROM   elevators
WHERE  license_status NOT IN ('INACTIVE', 'CANCELLED')
  AND  license_expiry BETWEEN CURRENT_DATE AND CURRENT_DATE + %s
ORDER  BY license_expiry ASC
```

---

## Query 7: "Which active elevators haven't been inspected in over a year?"

**Tool:** `list_overdue_inspections(days=365, limit=100)`
**Source:** `elevators, inspections`

Ontario elevator regulations require regular TSSA inspections. An active elevator that has gone more than a year without one is a compliance and safety liability. Elevators that have *never* been inspected appear first (they are the highest-priority gap). The `days` threshold and `limit` cap are both configurable so a compliance officer can tune the query for their workload without risking an overwhelming response.

```sql
WITH latest AS (
    SELECT DISTINCT ON (elevator_id)
           elevator_id, latest_date
    FROM   inspections
    ORDER  BY elevator_id, latest_date DESC NULLS LAST
)
SELECT e.id, e.location, e.device_type, e.license_status,
       l.latest_date AS last_inspection_date,
       (CURRENT_DATE - l.latest_date) AS days_since_inspection
FROM   elevators e
LEFT   JOIN latest l ON l.elevator_id = e.id
WHERE  e.license_status = 'ACTIVE'
  AND  (l.latest_date IS NULL OR l.latest_date < CURRENT_DATE - %s)
ORDER  BY l.latest_date ASC NULLS FIRST
LIMIT  %s
```

---

## Query 8: "What are the most common root causes of incidents across the fleet?"

**Tool:** `get_incident_root_cause_summary()`
**Source:** `incidents`

Individual incident reports tell you what happened to one elevator. Aggregated root cause data tells you what is systemically wrong across the entire fleet. If utility failures dominate, that points to infrastructure dependencies the team can address with building owners. If component defects lead, that signals a maintenance programme or supplier problem. A safety manager uses this query to justify budget requests, prioritise contractor audits, and brief executives on fleet-wide trends. Null root cause values (1,586 in the Ontario dataset) are surfaced explicitly as "Unknown / Not recorded" so they are visible rather than silently dropped.

```sql
SELECT COALESCE(root_cause, 'Unknown / Not recorded') AS root_cause,
       COUNT(*)                                        AS count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS percentage
FROM   incidents
GROUP  BY root_cause
ORDER  BY count DESC
```

---

## Query 9: "Which alteration requests are still awaiting a follow-up inspection?"

**Tool:** `list_alterations_pending_followup()`
**Source:** `alterations, elevators`

When an elevator is altered — whether a minor component swap or a major cab renovation — the alteration must be inspected and registered before the work is considered closed. "Pending Follow Up" status means the alteration has been submitted but the follow-up inspection has not yet been completed. With over 1,800 such open alterations in the Ontario dataset, this queue directly affects whether buildings can legally operate modified equipment. Operations teams use this list to chase outstanding inspections, prioritise contractor scheduling, and avoid compliance violations from altered-but-uninspected devices remaining in service.

```sql
SELECT a.id, a.elevator_id, e.location, e.device_type,
       a.alteration_type, a.summary, a.status, a.customer
FROM   alterations a
JOIN   elevators   e ON e.id = a.elevator_id
WHERE  a.status = 'Pending Follow Up'
ORDER  BY a.elevator_id, a.id
```
