# AND-104 Task 1 — CLAUDE.md Audit

## Rule Extraction and Categorisation

Seven rules were extracted from CLAUDE.md (including one embedded in the Directories section).

| # | Rule | Source | Category | Justification |
|---|------|---------|----------|---------------|
| 1 | Flask server opens via `python3 platform/server.py` (not by opening HTML directly) | Tech Stack section | SCOPED TO PLATFORM WORK | Only relevant when starting or working on the Flask platform; not needed in intelligence/, Go API, or docs/ work |
| 2 | `data/` — Ontario elevator datasets, do not modify | Directories section | **MUST ALWAYS EXECUTE** (hook candidate) | ~~ALWAYS RELEVANT~~ → upgraded after Task 3. Three systems now load from `data/` at startup: the Python Flask server, the Go API (`platform/api/`), and the ML pipeline. Accidental modification corrupts data silently across all three. Advisory text cannot prevent a Write or Edit tool call. A `PreToolUse` hook on `Write\|Edit` can block writes to existing source files deterministically. **Exception:** Task 6 must create `data/predictions.csv` (a new file). The hook must distinguish modification of existing files from creation of new ones. |
| 3 | Dashboard changes go through the spec first — edit `docs/dashboard_spec.md`, then regenerate `platform/index.html`; never edit HTML directly | Conventions | SCOPED TO PLATFORM WORK | Only fires when editing the dashboard page or spec; irrelevant to notebook, Go API, or data work |
| 4 | Run notebooks with the exact nbconvert command (`cd intelligence/` first, filename-only `--output`) | Conventions | ALWAYS RELEVANT | Applies whenever a notebook is executed, regardless of what else is being worked on. Advisory is sufficient: the cost of getting this wrong is a re-run, not data corruption. |
| 5 | Never include `Co-Authored-By: Claude` in commit messages | Conventions | MUST ALWAYS EXECUTE (hook candidate) | Applies to every commit. Task 3 reinforced this: the standard commit protocol would have appended `Co-Authored-By: Claude Sonnet 4.6` had the user not specified the exact message verbatim. A single missed instance persists permanently in git history. A `PreToolUse` hook on `Bash` matching `git commit` enforces this deterministically regardless of which path produces the commit. |
| 6 | Flask server is at `platform/server.py`; start with `python3 platform/server.py`; served at `http://localhost:5000` | Conventions | SCOPED TO PLATFORM WORK | Same intent as rule 1 with more detail; merged into one entry in the platform-conventions skill |
| 7 | HTMX endpoints return HTML fragments, not JSON; `/elevators` returns `<tbody>` for HTMX swap | Conventions | SCOPED TO PLATFORM WORK | Only relevant when writing or debugging Flask endpoints in `platform/`. Go API in `platform/api/` is a pure JSON service and never applies this rule. |

## Notes

- **Rules 1 and 6 merged** in the platform-conventions skill — both describe how to start the Flask server via `python3 platform/server.py`; duplicating them would create a maintenance burden.
- **Rule 2 upgraded (Task 3 revision):** Originally ALWAYS RELEVANT. Upgraded to MUST ALWAYS EXECUTE because the Go API now reads all six source CSVs at startup alongside the Flask server and ML pipeline. Advisory cannot prevent a Write tool call. See the hook design constraint in the table above: the hook must allow `data/predictions.csv` to be created (Task 6 dependency) while blocking writes to existing source files.
- **Rule 5 reinforced (Task 3 observation):** Category unchanged, but Task 3 provided concrete evidence — the default commit protocol would have added `Co-Authored-By: Claude Sonnet 4.6` if the user had not provided the exact commit message. The hook is not a "nice to have"; it is the only reliable enforcement path.
- **Rules moved to skill:** 1, 3, 6, 7 (spec-first workflow, Flask server startup, HTMX pattern).
- **Rules staying in CLAUDE.md:** 2 (data/), 4 (notebooks), 5 (commit message).
- **New pattern observed in Task 3 (not a CLAUDE.md rule):** `git add platform/api` staged the compiled Go binary `platform/api/api`, requiring a cleanup commit. This is not a rule in CLAUDE.md but is a hazard for any Go work in this repo. A `PreToolUse` hook on `Bash` matching `git add` could detect staged binary files and warn or block. Noted here as a hook candidate for future tasks if Go work expands.

## Hook 4 — Go build check (Task 3 friction, not a CLAUDE.md rule)

**Source:** New observation from Task 3 implementation; not one of the original seven CLAUDE.md rules.

**Problem it solves:** `platform/api/` is a three-file Go package (`main.go`, `data.go`, `handlers.go`) whose types are tightly coupled — `server` struct fields in `main.go` are referenced in both `data.go` and `handlers.go`; response types in `handlers.go` use internal row types from `data.go`. During Task 3, the first time all three files were compiled together was during the explicit `go build ./...` check at STEP 4. A cross-file type mismatch (e.g., adding a field to `server` in one file but mistyping it in another) would have been invisible across many edits until that point.

**Why a hook rather than a CLAUDE.md rule:** A CLAUDE.md rule ("run go build after each .go edit") can be skipped — especially during multi-file implementations where edits are intentionally in-progress. A PostToolUse hook fires after every Write/Edit/MultiEdit, regardless of context or Claude's current intent.

**Why a hook rather than a skill:** A skill requires invocation (user-triggered or Claude-decided). A PostToolUse hook fires automatically after each save. When three files are being edited in sequence, the hook catches the exact edit that breaks compilation, not only when a build check is explicitly requested.

**Implementation:** `PostToolUse` on `Edit|Write|MultiEdit`, second in the array (runs after `format-on-save.sh`). Checks that the file is in `platform/api/` and ends in `.go`; no-ops otherwise. Runs `go build ./...` from the module root; exits 1 with a stderr message (shown to Claude in transcript) on failure. Exit 0 on success (silent). PostToolUse is non-blocking regardless of exit code — exit 2 is not used.

## Hook design constraints confirmed from official schema

Read from `https://code.claude.com/docs/en/hooks` on 2026-06-03:

- **Blocking mechanisms for `PreToolUse`:** exit code 2 (ignores stdout, feeds stderr to Claude), OR exit 0 with JSON `hookSpecificOutput.permissionDecision: "deny"` (allows a structured reason message). For the commit-message hook, exit 2 with a stderr message is simplest; for the data-protection hook, `permissionDecision: "deny"` gives a cleaner user-facing message.
- **Matcher syntax:** bare alphanumeric strings are exact matches or `|`-separated lists; any other character triggers regex. `Bash` matches the Bash tool exactly. `Write|Edit` matches Write or Edit. This is confirmed — no wildcards needed for the two planned hooks.
- **Stop hook:** exit 0 for any notifier; exit 2 forces Claude to continue (do not use exit 2 in a notification hook).
- **stdin format:** hook receives JSON on stdin with `tool_name` and `tool_input` fields. For `Bash`, `tool_input.command` is the full shell command string to inspect.

_This document is a living audit. Categorisations reflect understanding as of AND-104 Task 4._

---

## Task 4: Development Workflow Hooks

Four hooks implemented in `.claude/settings.json` and `.claude/hooks/`. All tested by piping sample event JSON to each script and checking exit codes and output. Testing date: 2026-06-03.

---

### Hook 1 — `format-on-save.sh`

**Purpose:** Auto-run `gofmt -w` on `.go` files immediately after any Edit/Write/MultiEdit. Keeps Go code consistently formatted without a manual step; no-ops silently on every other file type.

**Event / Matcher:** `PostToolUse` → `Edit|Write|MultiEdit`

**Config:**
```json
{
  "type": "command",
  "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/format-on-save.sh"
}
```

**Test commands and observed results:**

```bash
# 1a — .go file with deliberate violations (extra spaces, missing tab)
echo '{"tool_name":"Edit","tool_input":{"file_path":".../platform/api/test_format.go",...}}' \
  | .claude/hooks/format-on-save.sh; echo $?
```
*Before:* `gofmt -l` reported file dirty. *After:* file clean — `import "fmt"` collapsed, `fmt.Println` lines got leading tab. **exit: 0** ✓

```bash
# 1b — non-.go file
echo '{"tool_name":"Write","tool_input":{"file_path":".../docs/api_spec.md",...}}' \
  | .claude/hooks/format-on-save.sh; echo $?
```
*No output, no file change.* **exit: 0** ✓

```bash
# 1c — already-clean .go file
echo '{"tool_name":"Edit","tool_input":{"file_path":".../platform/api/main.go",...}}' \
  | .claude/hooks/format-on-save.sh; echo $?
```
*No output, file unchanged.* **exit: 0** ✓

**Real edit trigger:** Confirmed via system hook — when the hook was first installed and `handlers.go` was passed as the test file, `gofmt` reformatted the file in place (spacing around struct field tags normalised).

---

### Hook 2 — `protect-data-files.sh`

**Purpose:** Block Write/Edit/MultiEdit to any existing source file inside `data/`. Three systems load from `data/` at startup (Flask server, Go API, ML pipeline); accidental modification is silent and corrupts all three. Advisory text in CLAUDE.md cannot prevent a Write tool call — only a PreToolUse hook can.

**Exception:** Files that do not yet exist (e.g. `data/predictions.csv`, generated in Task 6) are allowed through — the `-f` test blocks only pre-existing files.

**Event / Matcher:** `PreToolUse` → `Edit|Write|MultiEdit`

**Blocking mechanism:** exit 0 + `hookSpecificOutput.permissionDecision: "deny"` — produces a structured user-facing reason rather than a raw stderr dump.

**Config:**
```json
{
  "type": "command",
  "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/protect-data-files.sh"
}
```

**Test commands and observed results:**

```bash
# 2a — write to existing source file (absolute path)
echo '{"tool_name":"Write","tool_input":{"file_path":".../data/license.csv","content":"corrupted"}}' \
  | .claude/hooks/protect-data-files.sh; echo $?
```
*Output:* `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"READ-ONLY: .../data/license.csv is a source dataset. It is loaded at startup by the Flask server, Go API, and ML pipeline — modifying it corrupts all three. To add derived data, create a new file (e.g. data/predictions.csv does not yet exist and may be created freely)."}}` **exit: 0** ✓

```bash
# 2b — edit to existing source file (relative path)
echo '{"tool_name":"Edit","tool_input":{"file_path":"data/inspection.csv",...}}' \
  | .claude/hooks/protect-data-files.sh; echo $?
```
*permissionDecision:* `"deny"`. **exit: 0** ✓ (relative path resolved via `CLAUDE_PROJECT_DIR`)

```bash
# 2c — write to data/predictions.csv (does not yet exist — must allow)
echo '{"tool_name":"Write","tool_input":{"file_path":".../data/predictions.csv","content":"id,result"}}' \
  | .claude/hooks/protect-data-files.sh; echo $?
```
*No output — file allowed through.* **exit: 0** ✓

```bash
# 2d — edit to docs/api_spec.md (outside data/)
# 2e — edit to platform/api/main.go (outside data/)
```
*Both: no output, allowed.* **exit: 0** ✓

---

### Hook 3 — `notify-on-stop.sh`

**Purpose:** Send a desktop notification (`notify-send`) when Claude finishes a turn. Purely informational — the hook must always exit 0. Exiting 2 from a Stop hook forces Claude to keep working, which would create an infinite loop for a notification hook.

**`stop_hook_active` guard:** If the field is present and `true` in stdin, the script exits immediately without firing to prevent duplicate notifications if a stop event is re-entered.

**Event / Matcher:** `Stop` — no matcher (Stop has no matcher support per the schema).

**Config:**
```json
{
  "type": "command",
  "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/notify-on-stop.sh"
}
```

**Test commands and observed results:**

```bash
# 3a — normal stop
echo '{"hook_event_name":"Stop","session_id":"test-123","message_content":"Done.","tool_calls":[]}' \
  | .claude/hooks/notify-on-stop.sh; echo $?
```
**exit: 0** ✓

```bash
# 3b — stop_hook_active guard
echo '{"hook_event_name":"Stop","stop_hook_active":true}' \
  | .claude/hooks/notify-on-stop.sh; echo $?
```
*Returned immediately, no notification sent.* **exit: 0** ✓

```bash
# 3c — verify notify-send was actually called (PATH-intercept trace)
# Wrapped notify-send in a trace script capturing its arguments
```
*Captured:* `notify-send called: Claude Code Task complete.` — correct binary name and message. **exit: 0** ✓

```bash
# 3d — confirm never exits 2
echo '{"hook_event_name":"Stop"}' | .claude/hooks/notify-on-stop.sh; echo $?
```
**exit: 0** ✓ — PASS, not exit 2

**WSL2 note:** `notify-send` is installed at `/usr/bin/notify-send`. In WSL2 without a connected Linux GUI session the notification may not produce a visible window; `2>/dev/null || true` ensures the hook exits 0 regardless. The trace test above confirms the binary is called with the correct arguments.

---

### Hook 4 — `go-build-check.sh`

**Purpose:** Run `go build ./...` in `platform/api/` immediately after any `.go` edit. Catches cross-file type errors at the exact edit that introduces them, not only at the explicit build step before commit. In Task 3, `main.go`, `data.go`, and `handlers.go` share tightly coupled types; a field mismatch across files would have been invisible until the STEP 4 build check.

**Why a hook, not a CLAUDE.md rule:** A rule can be skipped mid-implementation when edits are intentionally in-progress. The hook fires on every save automatically.

**Why a hook, not a skill:** A skill requires invocation. The hook fires after every edit, catching the specific save that breaks compilation across coupled files.

**Event / Matcher:** `PostToolUse` → `Edit|Write|MultiEdit` (second in the hooks array, runs after format-on-save so gofmt normalises before build).

**Config:**
```json
{
  "type": "command",
  "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/go-build-check.sh",
  "timeout": 30
}
```

**Test commands and observed results:**

```bash
# 4a — clean .go file inside platform/api/
echo '{"tool_name":"Edit","tool_input":{"file_path":".../platform/api/handlers.go",...}}' \
  | .claude/hooks/go-build-check.sh; echo $?
```
*No output.* **exit: 0** ✓

```bash
# 4b — file outside platform/api/
echo '{"tool_name":"Edit","tool_input":{"file_path":".../docs/api_spec.md"}}' \
  | .claude/hooks/go-build-check.sh; echo $?
```
*No-op.* **exit: 0** ✓

```bash
# 4c — non-.go file inside platform/api/
echo '{"tool_name":"Write","tool_input":{"file_path":".../platform/api/README.md",...}}' \
  | .claude/hooks/go-build-check.sh; echo $?
```
*No-op.* **exit: 0** ✓

```bash
# 4d — deliberately broken: appended `func DELIBERATE_BREAK( {` to data.go
echo '{"tool_name":"Write","tool_input":{"file_path":".../platform/api/data.go",...}}' \
  | .claude/hooks/go-build-check.sh 2>&1; echo $?
```
*stderr:*
```
go build ./... failed after editing platform/api/data.go:
# github.com/charleswinfield108/Rocket_Dashboard/platform/api
./data.go:399:24: syntax error: unexpected {, expected )
```
**exit: 1** ✓ — compile error surfaced to Claude immediately

```bash
# 4e — post-restore: file reverted, clean build
```
**exit: 0** ✓
