# Code Review Report — AND-105 Task 4 (database-integration branch)

**Branch:** `database-integration` → `main`  
**Diff scope:** 4 commits, 21 files, +695 / −446 lines  
**Review date:** 2026-06-12  
**Sources:** worktree reviewer (claude --worktree db-reviewer), /code-review skill (7 finder angles + verifier pass), manual security review

---

## 1. Worktree Reviewer Findings

Independent review session run against the Task 4 diff (`database-integration` vs `main`).

### Blockers

| # | Location | Finding |
|---|----------|---------|
| B1 | `handlers.go:742` | `passRate` scanned into bare `float64` — NULL crash on empty inspections table |
| B2 | `handlers.go:150–169` | `lookupElevator` SELECT EXISTS is redundant for `handleGetElevator` and `handleGetRisk` — both already handle `pgx.ErrNoRows` → 404/503 |
| B3 | `db.go:47` | `sslmode=disable` hardcoded in DSN — no `DB_SSL_MODE` env override |
| B4 | `platform/api/` | Zero `*_test.go` files — entire DB layer is untested |

### Minors

| # | Location | Finding |
|---|----------|---------|
| M1 | `handlers.go:378` | `handleGetElevator` scans `e.id` back into `&id` — redundant scan of known value |
| M2 | `handlers.go:701,723` | `defer equipRows.Close()` + explicit close — defer is misleading; explicit close is load-bearing |
| M3 | `handlers.go:195` | Non-numeric `limit` returns range-violation message instead of parse-failure message |
| M4 | `handlers.go:208,377,...` | No `context.WithTimeout` on data handlers — stalled query holds pool connection indefinitely |
| M5 | `handlers.go:749` | `riskQ` duplicates `COUNT(*) FROM elevators` — already computed by `equipQ` |

---

## 2. /code-review Findings

7-angle finder pass + per-candidate verifier pass. Candidates rated CONFIRMED or PLAUSIBLE kept; REFUTED dropped (id aliasing in ErrNoRows path refuted — Scan never called on no-rows).

### Findings (ranked by severity)

| # | File | Line | Verdict | Summary |
|---|------|------|---------|---------|
| CR1 | `handlers.go` | 742 | PLAUSIBLE | `passRate float64` NULL scan crash on empty inspections table |
| CR2 | `db.go` | 47 | CONFIRMED | `sslmode=disable` hardcoded — no env override path |
| CR3 | `handlers.go` | 304 | PLAUSIBLE | `lookupElevator` SELECT EXISTS redundant in `handleGetElevator` — extra round-trip + TOCTOU |
| CR4 | `handlers.go` | 695 | PLAUSIBLE | Three sequential fleet-stats queries without snapshot isolation |
| CR5 | `handlers.go` | 208 | PLAUSIBLE | All data handlers use `r.Context()` with no deadline — stalled query exhausts pool |
| CR6 | `handlers.go` | 701 | CONFIRMED | `defer equipRows.Close()` misleading — explicit close at line 723 is load-bearing |
| CR7 | `handlers.go` | 377 | PLAUSIBLE | `e.id` scanned back into `&id` — redundant; aliasing risk on future refactor |
| CR8 | `handlers.go` | 195 | PLAUSIBLE | Non-numeric `limit` returns range message, not parse message |

#### CR1 — passRate NULL scan (detail)

```go
// SQL: NULLIF(COUNT(*),0) returns NULL when table is empty
// ROUND(NULL,4)::float8 = NULL
var passRate float64  // ← pgx cannot scan SQL NULL into non-pointer float64
s.db.QueryRow(ctx, inspQ).Scan(&totalInsp, &passRate)
```

**Failure scenario:** Empty `inspections` table → `NULLIF(COUNT(*),0)` = NULL → pgx error `unable to assign NULL to *float64` → handler returns 500 INTERNAL_ERROR.

**Fix (chosen — see Section 4):** Change `var passRate float64` to `var passRate *float64` and emit `0.0` when nil.

#### CR4 — Fleet-stats snapshot gap (detail)

`equipQ` scans `elevators` at T1. `riskQ` contains `(SELECT COUNT(*) FROM elevators)` running at T3. Concurrent ETL insert between T1 and T3 produces mismatched totals. Static ETL-only data makes this unlikely; structurally unsound.

#### CR5 — No handler deadline (detail)

`handleHealth` correctly wraps its context with a 2-second timeout (`db.go:83`). No data handler does. With `MaxConns=10`, ten concurrent stalled queries exhaust the pool.

---

## 3. Security Review Findings

| # | Severity | Dimension | Location | Description |
|---|----------|-----------|----------|-------------|
| S1 | HIGH | Sensitive data exposure | `handlers.go` (15 sites) | Raw pgx `err.Error()` strings in every 500 response body leak table/column names and constraint names. Fix: log internally, return fixed opaque message. |
| S2 | MEDIUM | Security misconfiguration | `db.go:47` | `sslmode=disable` hardcoded — no `DB_SSL_MODE` env var. Fix: read env var, default `disable`, document override for prod. |
| S3 | MEDIUM | Sensitive data exposure | `db.go:66,69,74,77` | Full DB connection coordinates logged unconditionally at startup (host, port, name). Low risk for internal tooling; cap before external deployment. |
| S4 | MEDIUM | Input validation | `handlers.go:207` | No length cap on `?status=` query param — arbitrarily long string allocated and sent to Postgres. Fix: cap at 64 chars. |
| S5 | MEDIUM | Input validation | `handlers.go:246` | No upper bound on `?page=` — `(page-1)*limit` produces astronomically large OFFSET. Fix: cap `page` at e.g. 10,000. |
| S6 | MEDIUM | Broken access control | `main.go:58–67` | No auth middleware on any route; elevator detail includes `billing_customer`, `billing_address`, `owner_name`, `owner_address` (PII). Must gate before any public exposure. |
| S7 | LOW | Error handling | `handlers.go:267–272` | Scan-error `writeError` inside `rows.Next()` loop is safe today (response not streamed) but fragile — a comment should confirm intent. |
| S8 | LOW | Path traversal | `data.go:161`, `main.go:37` | `DATA_DIR` env not confined to a base path after `filepath.Abs`. Defence-in-depth: add prefix check. |
| S9 | INFO | Injection | `handlers.go:210–244` | All SQL uses `$N` bind params — no injection risk confirmed. |
| S10 | INFO | Dependency | `go.mod:5` | `pgx/v5 v5.10.0` pinned. Confirm `go.sum` committed; run `govulncheck ./...` in CI. |

---

## 4. Fix Applied — CR1 / B1: passRate NULL scan

**File:** `platform/api/handlers.go:742`  
**Change:** `var passRate float64` → `var passRate *float64`; emit `0.0` when nil.

```go
// Before
var passRate float64
if err := s.db.QueryRow(ctx, inspQ).Scan(&totalInsp, &passRate); err != nil { ... }

// After
var passRatePtr *float64
if err := s.db.QueryRow(ctx, inspQ).Scan(&totalInsp, &passRatePtr); err != nil { ... }
passRate := 0.0
if passRatePtr != nil {
    passRate = *passRatePtr
}
```

**Why this finding, not CR2 (sslmode):** The passRate scan is a crash path reachable at runtime on a valid (empty) database state. The sslmode issue is a configuration inflexibility that only manifests at deploy time in environments not currently targeted. A crash on valid DB state is higher priority for a PR fix.

---

## 5. Outstanding Items (not fixed in this PR)

| Priority | Item | Tracking |
|----------|------|---------|
| High | Add `DB_SSL_MODE` env var override to `db.go` | Future PR |
| High | Add `*_test.go` files for DB layer | Future PR |
| Medium | Wrap data handler contexts with `context.WithTimeout` | Future PR |
| Medium | Remove redundant `lookupElevator` from `handleGetElevator` | Future PR |
| Low | Remove `defer equipRows.Close()` — keep explicit close only | Future PR |
| Low | Remove `e.id` from `handleGetElevator` SELECT / scan into `var dbID int` | Future PR |
| Low | Fix non-numeric `limit` error message | Future PR |
| Low | Wrap fleet-stats in a repeatable-read transaction | Future PR |
