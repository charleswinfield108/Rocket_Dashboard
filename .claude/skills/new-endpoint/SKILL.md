---
name: new-endpoint
description: Adds a new Go API endpoint end-to-end: updates the spec, generates the handler, registers the route, and validates conformance. Usage: /new-endpoint <path> "<description>"
user-invocable: true
---

# Task 7: Fleet Health Feature

The user has invoked `/new-endpoint` with arguments: `$ARGUMENTS`

The first argument is the endpoint path (e.g. `fleet-stats`). The second argument is a quoted description (e.g. `"Returns aggregate fleet statistics"`).

Work through the five steps below in order. Do not skip ahead — each step depends on the previous one being correct and complete.

---

## STEP 0 — DATA PROFILE

Before writing any spec or code, spawn the `data-profiler` subagent to inspect the CSV files this endpoint will read from.

Identify which of the following source files are relevant to the endpoint being built:

| File | Contents | Join key |
|------|----------|----------|
| `data/merged_elevator_data.csv` | Elevator static data | `ElevatingDevicesNumber` |
| `data/inspection.csv` | Inspection records | `ElevatingDevicesNumber` |
| `data/order.csv` | Compliance orders | `ElevatingDevicesNumber` / `inspectionnumber` |
| `data/predictions.csv` | ML risk predictions | `elevator_id` (format `EL-XXXXXXXX`) |

Pass the relevant files and their shared join key to the data-profiler subagent. Ask it specifically to:
1. Report row counts, enum distributions, and date-column format samples for each file
2. Compute the join coverage matrix for all file pairs (matched vs. orphan rows in each direction)
3. Flag any date columns NOT already in ISO 8601 format — the Go server normalizes these at load time, so raw string comparisons on un-normalized dates will give incorrect results
4. Flag any join direction where `len(A) - len(B)` would give a wrong "unmatched" count

**Do not proceed to STEP 1 until the data-profiler report is complete.** Use the findings to inform the response shape in STEP 1 and the implementation in STEP 2. In particular:
- If a join gives orphan rows, use a join-based count (iterate and check membership) rather than subtracting lengths
- If a date column is not ISO 8601, do not compare raw date strings — use the Go server's normalized values from in-memory structs

---

## STEP 1 — SPEC UPDATE

Read `docs/api_spec.md` in full. Identify the highest-numbered section under `§5` and insert a new section immediately after it for the new endpoint.

The new spec section must include all of the following:

**HTTP method and path**
State the method (`GET`, `POST`, etc.) and the full path pattern (e.g. `GET /api/fleet-stats`).

**Description**
One to three sentences describing what the endpoint does and what data it draws from.

**Query parameters**
A table listing every query parameter: name, type, required/optional, default value, constraints, and description. If there are no query parameters, write "None."

**Response — 200 OK**
A fenced JSON block showing a complete, realistic example response. Every field in the response schema must appear in the example. Use real-looking values, not placeholders like `"string"` or `0`.

**Response field types table**
A markdown table with columns: Field, JSON type, Source column, Source file. Every field in the example must have a row.

**Error responses**
A table of error HTTP status codes, `error` code strings, and the conditions that trigger them. Include at minimum:
- `500 INTERNAL_ERROR` for unexpected failures
- `404 ELEVATOR_NOT_FOUND` if the endpoint takes an `{id}` path parameter

After writing the spec section, print it back to confirm it was written correctly before moving to STEP 2.

---

## STEP 2 — CODE GENERATION

Read the existing handler files in `platform/api/` to understand the project conventions before writing any code:
- `main.go` — server struct, config, startup
- `data.go` — CSV loading pattern, helper functions (`readCSV`, `colIdx`, `cell`, `mustFloat`, `optStr`, etc.)
- `handlers.go` — handler function signature, `writeJSON`, `writeError`, response struct patterns

Generate a new handler function in `platform/api/handlers.go` (append to the file — do not replace existing content) that:

- Has the signature `func (s *server) handle<Name>(w http.ResponseWriter, r *http.Request)`
- Reads from the relevant CSV source(s) via the shared `readCSV` / `colIdx` / `cell` helpers — no hardcoded data
- Uses the existing `s.cfg.dataDir` to resolve file paths
- Returns the response shape defined in STEP 1 exactly — field names and types must match
- Handles errors: file-not-found → `writeError(w, 500, "INTERNAL_ERROR", ...)`, malformed required fields → skip the row and continue (match the existing pattern in `loadElevators`)
- Uses `writeJSON` to return the 200 response

If new response struct types are needed, add them to `handlers.go` immediately above the new handler function.

---

## STEP 3 — ROUTE REGISTRATION

Open `platform/api/main.go`. In the `routes()` method, register the new handler alongside the existing four routes. Match the existing pattern exactly:

```go
mux.HandleFunc("GET /api/<path>", s.handle<Name>)
```

After editing, run:

```bash
cd platform/api && go build ./...
```

If the build fails, read the compiler error, fix it, and rebuild. Do not proceed to STEP 4 until the build is clean.

Confirm the four existing routes are still registered and unchanged.

---

## STEP 4 — VALIDATION

Run `/validate-api /api/<path>` against the new endpoint.

If the result is **CONFORMS**, report success and summarise what was added:
- The spec section added (section number and title)
- The handler function name
- The route registered
- The validate-api result

If the result is **DOES NOT CONFORM**:
- Identify the failing dimension(s)
- Show the spec snippet, the relevant source data, and the handler code for each failure
- Apply the minimal fix
- Re-run `/validate-api` and confirm CONFORMS before reporting completion

Do not consider this workflow complete until `/validate-api` reports **CONFORMS**.
