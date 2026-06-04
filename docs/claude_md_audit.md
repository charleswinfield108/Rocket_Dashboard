# AND-104 Task 1 — CLAUDE.md Audit

## Rule Extraction and Categorisation

Seven rules were extracted from CLAUDE.md (including one embedded in the Directories section).

| # | Rule | Source | Category | Justification |
|---|------|---------|----------|---------------|
| 1 | Flask server opens via `python3 platform/server.py` (not by opening HTML directly) | Tech Stack section | SCOPED TO PLATFORM WORK | Only relevant when starting or working on the Flask platform; not needed in intelligence/ or docs/ work |
| 2 | `data/` — Ontario elevator datasets, do not modify | Directories section | ALWAYS RELEVANT | Applies to all work; any layer could accidentally touch source data |
| 3 | Dashboard changes go through the spec first — edit `docs/dashboard_spec.md`, then regenerate `platform/index.html`; never edit HTML directly | Conventions | SCOPED TO PLATFORM WORK | Only fires when editing the dashboard page or spec; irrelevant to notebook or data work |
| 4 | Run notebooks with the exact nbconvert command (`cd intelligence/` first, filename-only `--output`) | Conventions | ALWAYS RELEVANT | Applies whenever a notebook is executed, regardless of what else is being worked on |
| 5 | Never include `Co-Authored-By: Claude` in commit messages | Conventions | MUST ALWAYS EXECUTE (hook candidate) | Applies to every commit; a single missed instance in hundreds of commits is a real risk — deterministic hook enforcement preferred over advisory text |
| 6 | Flask server is at `platform/server.py`; start with `python3 platform/server.py`; served at `http://localhost:5000` | Conventions | SCOPED TO PLATFORM WORK | Same intent as rule 1 with more detail; merged into one entry in the skill |
| 7 | HTMX endpoints return HTML fragments, not JSON; `/elevators` returns `<tbody>` for HTMX swap | Conventions | SCOPED TO PLATFORM WORK | Only relevant when writing or debugging Flask endpoints in platform/ |

## Notes

- **Rules 1 and 6 merged** in the platform-conventions skill — both describe how to start the Flask server via `python3 platform/server.py`; duplicating them would create a maintenance burden.
- **Rule 5 is a hook candidate**, not a skill entry. A skill is advisory text that can be ignored; a PreToolUse hook on git commands executes deterministically regardless of context. The rule stays in CLAUDE.md for now and will move to a hook in AND-104 Task 4.
- **Rules moved to skill:** 1, 3, 6, 7 (spec-first workflow, Flask server startup, HTMX pattern).
- **Rules staying in CLAUDE.md:** 2 (data/), 4 (notebooks), 5 (commit message).

_This document is a first-pass audit. It will be updated as hooks are implemented in later AND-104 tasks._
