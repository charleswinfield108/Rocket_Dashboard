# Code Review Report — AND-105 Task 5: Multi-Source Review of Database Integration (Task 4)

**Branch:** `database-integration` → `main`
**Diff scope:** Commits `b7b9be6`–`861fa86` (5 commits, ~1 465 diff lines across `db.go`, `handlers.go`, `main.go`, `data.go`, `go.mod`)
**Review date:** 2026-06-12
**Review methods:**
1. **Reviewer session** — `claude --worktree db-reviewer` independent worktree session
2. **Fan-out /code-review** — 7-angle parallel finder pass + per-candidate verifier pass
3. **/code-review** — GitHub Copilot built-in `/code-review` on Task 4 diff
4. **/security-review** — GitHub Copilot built-in `/security-review` on Task 4 diff

All SQL parameterisation confirmed clean (no injection): `/security-review` INFO finding S9. `go.sum` committed; `pgx/v5 v5.10.0` pinned.

---

## CRITICAL — Must Fix

Findings in this section are runtime crashes, production-path data leaks, or exploitable
vulnerabilities. Items marked ✅ were fixed before merge. ⚠️ items remain open.

Overlap across multiple methods is a severity signal: each independent method that surfaces
the same finding provides independent corroboration.

---

### C1 · `passRate` scanned into non-pointer `float64` — runtime crash on empty inspections table

**Status:** ✅ Fixed — commit `99efc09`
**Surfaced by:** Reviewer session (B1) · Fan-out /code-review (CR1, PLAUSIBLE) · /code-review (CR-2)
**Overlap: 3 of 4 methods** — highest co-occurrence in the review set.

`NULLIF(COUNT(*), 0)::float8` in `inspQ` returns SQL NULL when the inspections table is empty.
pgx v5 cannot scan SQL NULL into a bare `float64`; it returns a scan error that propagates as
500 INTERNAL_ERROR on `GET /api/fleet/stats`.

```go
// Before — crashes on empty inspections table
var passRate float64
s.db.QueryRow(ctx, inspQ).Scan(&totalInsp, &passRate)

// After — fix applied in 99efc09
var passRatePtr *float64
s.db.QueryRow(ctx, inspQ).Scan(&totalInsp, &passRatePtr)
passRate := 0.0
if passRatePtr != nil {
    passRate = *passRatePtr
}
```

---

### C2 · `sslmode=disable` hardcoded — no TLS on any DB connection

**Status:** ✅ Fixed — commit `4a64747` (WR2)
**Surfaced by:** Reviewer session (B3) · Fan-out /code-review (CR2, CONFIRMED) · /security-review (SR-1)
**Overlap: 3 of 4 methods**

All PostgreSQL traffic — including the authentication handshake carrying `DB_PASSWORD` and every
query result containing PII (billing customers, owner names, addresses) — flowed over plaintext
TCP. No environment-variable escape hatch existed; the binary always connected without TLS
regardless of deployment environment.

**Fix applied:** `DB_SSL_MODE` env var read via `os.Getenv`; DSN switched to URL form
(`postgresql://`) so SSL mode is controllable without recompilation.

---

### C3 · DSN password interpolated into libpq keyword=value string — silent misparse

**Status:** ✅ Fixed — commit `4a64747` (WR2, same commit as C2)
**Surfaced by:** /security-review (SR-2) · Reviewer session (WR2, post-merge catch)
**Overlap: 2 of 4 methods**

```go
// Before — fragile
"host=%s port=%s dbname=%s user=%s password=%s sslmode=disable",
c.host, c.port, c.name, c.user, c.password
```

libpq keyword=value parsing treats spaces, `=`, `'`, and `\` as syntactically significant. A
password containing any of those characters silently truncates or misparses the DSN — either
failing to connect or, worse, stripping the `sslmode` directive so the suffix is misread as a
different option value.

**Fix applied:** URL DSN form with `url.QueryEscape(c.user)` / `url.QueryEscape(c.password)`.
The `/security-review` pass classified this as OWASP A03 (injection via DSN); the reviewer
session caught it independently as a portability bug. The convergence of two methods on a
non-obvious encoding issue was the trigger for the post-merge fix commit.

---

### C4 · Raw `pgx err.Error()` strings returned in all 500 response bodies — information disclosure

**Status:** ✅ Fixed — see below
**Surfaced by:** /security-review (SR-3, HIGH) · Reviewer session (security pass, S1)
**Overlap: 2 of 4 methods**

Fifteen `writeError` call sites pass `"... "+err.Error()` directly as the HTTP response body.
pgx error strings embed PostgreSQL severity level, SQLSTATE codes, table names, column names,
and constraint names. The most exposed site is `handleHealth`, which returns a detailed pgx
error to any unauthenticated caller:

```
"database ping failed: ERROR: password authentication failed for user \"api\" (SQLSTATE 28P01)"
```

This leaks database type, version, schema structure, and internal topology. `/code-review` noted
the same strings as "verbose" — a style concern. `/security-review` reclassified them as OWASP
A05 (Security Misconfiguration / Information Disclosure) with a different, mandatory remediation:
log `err` server-side, return only the fixed error code to the client.

```go
// Remediation pattern for all 15 sites
log.Printf("handleGetElevator id=%d: %v", id, err)
s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "internal error")
```

---

## WARNINGS — Should Fix

Issues that do not crash today but will under realistic load or configuration, or represent
confirmed API contract changes that may break existing clients.

---

### W1 · No context deadline on data handlers — pool starvation under load

**Status:** ⚠️ Outstanding
**Surfaced by:** Reviewer session (M4) · Fan-out /code-review (CR5, PLAUSIBLE)
**Overlap: 2 of 4 methods**

`handleHealth` correctly wraps `r.Context()` in a 2-second timeout (`db.go`). No data handler
does. With `MaxConns=10`, ten concurrent stalled queries (PostgreSQL vacuum lock, network
partition, slow client) permanently exhaust the pool; all subsequent requests queue indefinitely.

**Remediation:** `ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second); defer cancel()`
at the top of each data handler.

---

### W2 · `lookupElevator` SELECT EXISTS is redundant for two of three callers

**Status:** ⚠️ Outstanding
**Surfaced by:** Reviewer session (B2) · Fan-out /code-review (CR3, PLAUSIBLE) · /code-review (CR-1)
**Overlap: 3 of 4 methods**

`lookupElevator` fires `SELECT EXISTS(SELECT 1 FROM elevators WHERE id = $1)` before all three
per-elevator handlers. `handleGetElevator` and `handleGetRisk` both already handle `pgx.ErrNoRows`
with correct 404/503 responses — the EXISTS check adds a full DB round-trip with no benefit.
Only `handleGetInspections` genuinely needs it, because an unknown elevator returns `200 + []`
rather than ErrNoRows from the inspections query.

**Remediation:** Remove `lookupElevator` from `handleGetElevator` and `handleGetRisk`; keep for
`handleGetInspections` only.

---

### W3 · `asOfDate` scanned into non-pointer `string` — crash if `prediction_date` is NULL

**Status:** ⚠️ Outstanding
**Surfaced by:** /code-review (CR-3) — unique to this review pass
**Overlap: 1 of 4 methods**

`TO_CHAR(prediction_date, 'YYYY-MM-DD')` returns SQL NULL when `prediction_date` IS NULL. pgx v5
cannot scan SQL NULL into a bare `string` variable (`var asOfDate string`, `handlers.go:565`).
This is structurally identical to C1 and would surface as a 500 on `GET /api/elevators/{id}/risk`
for any elevator whose prediction row has a NULL prediction date. The ETL currently writes
non-NULL dates, but the query provides no defence if that invariant ever breaks.

**Remediation:** `var asOfDate *string`; emit `""` in the response when nil — or add a NOT NULL
constraint to `predictions.prediction_date` in the schema.

---

### W4 · No authentication middleware — PII endpoints fully public

**Status:** ⚠️ Outstanding
**Surfaced by:** /security-review (S6, MEDIUM) — unique to this review pass
**Overlap: 1 of 4 methods**

`GET /api/elevators/{id}` returns `billing_customer`, `billing_address`, `owner_name`,
`owner_address` with no token, session, or IP restriction on any route. Acceptable for
localhost-only use; a hard blocker before any external or network-accessible deployment.

---

### W5 · `RiskLevels` JSON shape changed from `null` to zero-value object — silent contract break

**Status:** ⚠️ Outstanding
**Surfaced by:** /code-review (CR-5) — unique to this review pass
**Overlap: 1 of 4 methods**

Old behaviour: `"risk_levels": null` when `predictionsLoaded` was false. New behaviour: always
emits `{"high":0,"medium":0,"low":0,"unscored":N}`, even when the predictions table is empty.
Any client asserting `risk_levels == null` silently receives a zero-valued object.

**Remediation:** Conditionally emit null when the predictions table is empty, or explicitly
document the new shape in the API spec.

---

### W6 · Fleet-stats three queries run without snapshot isolation

**Status:** ⚠️ Outstanding
**Surfaced by:** Fan-out /code-review (CR4, PLAUSIBLE) — unique to this review pass
**Overlap: 1 of 4 methods**

`equipQ` scans the elevators table at T1. `riskQ` contains `(SELECT COUNT(*) FROM elevators)`
executing at T3. A concurrent ETL insert between T1 and T3 produces a `total_elevators` mismatch
within the same response. Static ETL-only data makes this unlikely; the structure is unsound.

**Remediation:** Wrap all three queries in `BEGIN; SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;`.

---

### W7 · Unbounded `?status=` string and `?page=` integer

**Status:** ⚠️ Outstanding
**Surfaced by:** /security-review (S4, S5, MEDIUM) — unique to this review pass
**Overlap: 1 of 4 methods**

`?status=` accepts an arbitrarily long string (unbounded heap allocation sent as a SQL parameter).
`?page=` is uncapped — `(page-1)*limit` produces an arbitrarily large OFFSET that triggers a
full sequential scan of the elevators table.

**Remediation:** `if len(statusFilter) > 64 { reject }`. Cap `page` at `(total/limit)+1` or a
hard maximum of 10 000.

---

## SUGGESTIONS — Worth Considering

Low-urgency items: efficiency, readability, or defence-in-depth hardening.

---

### S1 · `items` slices not pre-allocated with known capacity bound

**Surfaced by:** /code-review (CR-6)

`handleListElevators`, `handleGetInspections`, and `handleFleetAlerts` all use `make([]T, 0)`.
`handleListElevators` knows it will append at most `limit` rows. `make([]fleetItem, 0, limit)`
avoids repeated backing-array reallocations.

---

### S2 · `defer equipRows.Close()` + explicit `equipRows.Close()` — reads as dead code

**Surfaced by:** Reviewer session (M2) · Fan-out /code-review (CR6, CONFIRMED) · /code-review (CR-4)
**Overlap: 3 of 4 methods**

The explicit close is load-bearing (releases the pool connection back before Query 2 starts).
The `defer` is correct as a fallback if the loop exits early via `return`. Without a comment,
every reader flags the explicit close as dead code.

**Remediation:** Add inline comment: `// explicit: returns connection to pool before Query 2; defer is fallback on early return`.

---

### S3 · `e.id` redundantly scanned into `&id` in `handleGetElevator`

**Surfaced by:** Reviewer session (M1) · Fan-out /code-review (CR7, PLAUSIBLE — aliasing risk refuted by verifier)
**Overlap: 2 of 4 methods**

`SELECT ... WHERE e.id = $1` always returns the same value that `id` already holds. The fan-out
verifier explicitly refuted a corrupted-id aliasing risk (`pgx.ErrNoRows` exits before `Scan`
is ever called). Cosmetic cleanup only.

---

### S4 · Non-numeric `limit` returns range-violation message instead of parse-failure message

**Surfaced by:** Reviewer session (M3) · Fan-out /code-review (CR8, PLAUSIBLE)
**Overlap: 2 of 4 methods**

`parseQueryInt("abc", 100)` returns a parse error. The handler's `if err != nil` branch emits
`"limit must be between 1 and 500"` — a range-constraint message for a non-numeric input.

---

### S5 · `riskQ` repeats `COUNT(*) FROM elevators` — already computed by `equipQ`

**Surfaced by:** Reviewer session (M5)

`equipQ` accumulates `totalElevators` in the scan loop. `riskQ` runs a subquery
`(SELECT COUNT(*) FROM elevators)` independently. Reusing `totalElevators` removes one subquery
execution per `/fleet/stats` request.

---

### S6 · DB connection coordinates logged unconditionally at startup

**Surfaced by:** /security-review (S3, LOW)

`log.Printf("DB: connecting to %s:%s/%s", ...)` emits host, port, and database name on every
startup. Low risk for an internal dashboard; worth moving behind a `DEBUG` flag before any
deployment where logs are externally accessible.

---

### S7 · `DATA_DIR` not confined to a base path after resolution

**Surfaced by:** /security-review (S8, LOW)

`filepath.Abs` resolves `DATA_DIR` but does not guard against path-traversal values such as
`../../etc`. Defence-in-depth: add `strings.HasPrefix(resolved, expectedBase)` after `filepath.Abs`.

---

## Overlap Summary

| Finding | Reviewer session | Fan-out /code-review | /code-review | /security-review | Count |
|---------|:---:|:---:|:---:|:---:|:---:|
| C1 passRate NULL crash | ✓ | ✓ | ✓ | — | **3** |
| C2 sslmode hardcoded | ✓ | ✓ | — | ✓ | **3** |
| C3 DSN password misparse | ✓ | — | — | ✓ | **2** |
| C4 err.Error() disclosure | ✓ | — | — | ✓ | **2** |
| W1 no handler deadline | ✓ | ✓ | — | — | **2** |
| W2 lookupElevator double RTT | ✓ | ✓ | ✓ | — | **3** |
| W3 asOfDate NULL scan | — | — | ✓ | — | 1 |
| W4 no auth middleware | — | — | — | ✓ | 1 |
| W5 RiskLevels shape change | — | — | ✓ | — | 1 |
| W6 fleet-stats no isolation | — | ✓ | — | — | 1 |
| W7 unbounded params | — | — | — | ✓ | 1 |
| S1 no capacity hint | — | — | ✓ | — | 1 |
| S2 double Close() | ✓ | ✓ | ✓ | — | **3** |
| S3 redundant &id scan | ✓ | ✓ | — | — | **2** |
| S4 limit error message | ✓ | ✓ | — | — | **2** |
| S5 riskQ duplicate COUNT | ✓ | — | — | — | 1 |
| S6 startup log | — | — | — | ✓ | 1 |
| S7 DATA_DIR traversal | — | — | — | ✓ | 1 |

Items with count ≥ 2 were surfaced by independent methods with no coordination — overlap is a
reliable severity signal, not confirmation bias.

---

## VERDICT

**Overall assessment:** The database integration is structurally sound. The migration from
in-memory CSV state to a persistent, parameterised SQL layer is clean: all SQL uses `$N` bind
parameters throughout (no injection risk confirmed by /security-review); the connection pool is
properly bounded, warmed at startup with a ping, and — post-fix — uses URL-encoded credentials
with a configurable SSL mode.

**Two critical findings were caught and fixed before merge** — the `passRate` NULL scan crash
(raised by 3 of 4 methods) and the `sslmode=disable`/DSN-misparse pair (also 3 of 4 methods).
The multi-source review demonstrably earned its cost: both were production-path runtime failures
that a single-pass code read would likely have missed.

**The sharpest divergence between `/code-review` and `/security-review`:**

- **C4 (verbose error bodies):** `/code-review` flagged these as "verbose" — a style concern.
  `/security-review` reclassified them as OWASP A05 information disclosure with a mandatory
  remediation (log internally, return opaque codes). Same line of code; different severity
  classification and different fix. This is the clearest case where the two passes are not
  interchangeable.
- **W4 (no auth middleware):** entirely invisible to `/code-review` — correctness review has no
  concept of "who shouldn't be able to call this endpoint." `/security-review` caught it as a
  structural access-control gap. Coverage that only security review provides.
- Conversely, `/code-review` exclusively caught W3 (asOfDate NULL scan), W5 (RiskLevels shape
  change), and S1 (capacity hint) — runtime-path correctness and API contract items that
  `/security-review` did not examine.

**One outstanding critical item (C4)** should be addressed before any deployment outside
localhost. Stripping `err.Error()` from HTTP responses is a one-pass change across 15 call
sites. W1 (handler deadlines) and W2 (lookupElevator redundancy) are the priority items for
the next PR.

**Approved for merge** with C1/C2/C3 resolved. C4, W1, and W2 tracked as next-PR work.
