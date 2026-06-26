# Additional Chatbot Queries — AND-107

Beyond the five required queries, the following additional queries have been identified based on the data available in the PostgreSQL database (elevators, inspections, incidents, alterations, predictions tables).

---

## Query 6: "Which elevators have licences expiring in the next 90 days?"

**Why an operations team member needs this:**
Licence expiry is a compliance deadline. If a licence lapses, the elevator must be taken out of service immediately — which means tenant disruption, potential fines, and an emergency re-licensing process. An operations manager running a building portfolio needs advance warning to start renewal paperwork before the expiry date, not after. Pulling this list proactively is the difference between a routine renewal and an emergency shutdown.

**Data source:** `elevators.license_expiry`, `elevators.license_status`

---

## Query 7: "Which elevators are high risk and have not been inspected in the last 12 months?"

**Why an operations team member needs this:**
The predictions table gives each elevator a risk score and risk level. A high-risk elevator that has also gone more than a year without an inspection is a compounding liability — elevated probability of a bad outcome, and no recent TSSA verification that the device is safe. This is exactly the prioritisation signal a compliance officer needs to decide which sites to visit next. Neither the risk score alone nor the inspection date alone tells the full story; it is the combination that creates urgency.

**Data source:** `predictions.risk_level`, `inspections.latest_date` (most recent per elevator)

---

## Query 8: "What are the most common root causes of incidents across the fleet?"

**Why an operations team member needs this:**
Individual incident reports tell you what happened to one elevator. Aggregated root cause data tells you what is systemically wrong across the fleet. If mechanical failure accounts for 60% of incidents, that points to a maintenance programme problem. If human error is rising, that points to a training gap. A safety manager uses this query to justify budget requests, prioritise contractor audits, and brief executives on fleet-wide risk trends — none of which is possible from looking at incidents one at a time.

**Data source:** `incidents.root_cause`, `incidents.category`

---

## Query 9: "Which elevators have had more than two incidents in the past three years?"

**Why an operations team member needs this:**
A single incident can be a one-off. Two or more incidents on the same device within a few years indicates a recurring problem — bad installation, inadequate maintenance, or a design deficiency that keeps resurfacing. Operations teams use repeat-incident lists to flag devices for closer contractor oversight, push for major alteration reviews, or escalate to building owners. Without this query, repeat offenders hide inside a large incident log and never get the focused attention they need.

**Data source:** `incidents.elevator_id`, `incidents.date_of_occurrence`
