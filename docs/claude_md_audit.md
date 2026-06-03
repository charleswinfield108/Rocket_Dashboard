# AND-104 Task 1: CLAUDE.md Audit and Platform Conventions

*Created: 2026-05-30*

This document categorises every rule in `CLAUDE.md` into one of three buckets, and records the justification for each decision. It is a **first-pass categorisation** — categories and justifications will be revisited and refined as hooks are implemented in Task 4. The goal is that this audit always reflects current understanding, not that every decision is final on the first attempt.

---

## The Three Buckets

| Bucket | Meaning | Where it lives |
|---|---|---|
| **ALWAYS RELEVANT** | Applies to all work regardless of layer — intelligence, platform, docs, Go API | Stays in `CLAUDE.md` |
| **MUST ALWAYS EXECUTE** | A hard, deterministic action that must fire on every relevant event — cannot be enforced by advisory text alone | → Hook (implemented in Task 4) |
| **SCOPED TO PLATFORM WORK** | Only relevant when editing files in `platform/` — Python web dev, Flask, HTMX, server conventions | → Skill (`.claude/skills/platform-conventions/SKILL.md`) |

---

## Rule-by-Rule Categorisation

| # | Rule | Category | Justification |
|---|---|---|---|
| 1 | *Tech Stack section:* "The dashboard is served by a Flask server — open via `python3 platform/server.py`, not by opening the HTML file directly." | **SCOPED TO PLATFORM WORK** | Only relevant when accessing or running the dashboard; has no bearing on notebook or documentation work. *(Merged with rule 6 in the skill — both describe how to start the server.)* |
| 2 | *Directories section (`data/`):* "do not modify" | **ALWAYS RELEVANT** | The `data/` files are the shared source of truth for every layer — notebooks, Go API, and Python frontend all read from them; the constraint applies everywhere. |
| 3 | *Conventions:* "Dashboard changes go through the spec first. Edit `docs/dashboard_spec.md`, then regenerate `platform/index.html`. Do not edit the HTML directly." | **SCOPED TO PLATFORM WORK** | Only applies when modifying the dashboard frontend; irrelevant when working in notebooks, Go API, or docs. |
| 4 | *Conventions:* Run notebooks with `cd intelligence && /usr/bin/python3 -m jupyter nbconvert --to notebook --execute <notebook>.ipynb --output <notebook>.ipynb --ExecutePreprocessor.timeout=120` — always `cd` into `intelligence/` first; pass a filename-only `--output` (not a path) to avoid nbconvert doubling the directory prefix. | **ALWAYS RELEVANT** | Applies to the intelligence layer regardless of which other layer is being worked on; not platform-specific. |
| 5 | *Conventions:* "Never include `Co-Authored-By: Claude` in commit messages." | **MUST ALWAYS EXECUTE** | A hard constraint on every commit regardless of layer — advisory text in CLAUDE.md can be overlooked; a PreToolUse hook on Bash/git commands cannot be. |
| 6 | *Conventions:* "Flask server is at `platform/server.py`. Start with `python3 platform/server.py`. The dashboard is served at `http://localhost:5000`." | **SCOPED TO PLATFORM WORK** | Only relevant when running or developing the Python frontend; meaningless in the context of notebooks or documentation. *(Merged with rule 1 in the skill.)* |
| 7 | *Conventions:* "HTMX endpoints return HTML fragments, not JSON. The `/elevators` endpoint returns a `<tbody>` fragment for HTMX to swap into the page." | **SCOPED TO PLATFORM WORK** | A Flask/HTMX architectural constraint that only matters when writing or reading server endpoints in `platform/`. |

---

## Migration Summary

| Destination | Rules |
|---|---|
| Stays in `CLAUDE.md` | 2, 4 |
| Hook candidate (Task 4) | 5 |
| Moves to `.claude/skills/platform-conventions/SKILL.md` | 1, 3, 6, 7 (rules 1 and 6 merged into one entry) |

---

## Notes and Open Questions

- **Rules 1 and 6 overlap:** both describe starting the server with `python3 platform/server.py`. They are merged into a single entry in the skill rather than duplicated.
- **Rule 5 (commit message hook):** flagged as a hook candidate but not yet implemented. Will be addressed in Task 4. Until then the rule remains in `CLAUDE.md` as an advisory note.
- **Tech stack and directory context** (project description, stack list, directory map, data file list) are reference context rather than actionable rules and are retained in `CLAUDE.md` unchanged.

---

## Task 4 Hook Implementations

*(This section will be populated in Task 4 once hooks are built and tested.)*