# AND-104 Extending AI Tools Business Document
## Module 4 Overview

This module introduces three mechanisms for extending Claude Code beyond its defaults: hooks (deterministic automation that always executes), skills (modular instructions that load on demand), and custom subagents (delegation with a scoped role). You will build these extensions as you add a Go JSON API alongside your existing Python server, deploy your ML predictions as a live API endpoint, and add fleet-level health monitoring.

By the end of this module, your dashboard will have a working backend API in Go, your ML predictions will be served through the API with risk indicators on the dashboard, and fleet health statistics and alerts will be available to the operations team. Your Claude Code environment will be customized with hooks, skills, and a subagent that make your development workflow faster and more reliable.

This module includes learning cards with optional practice exercises. These exercises are recommended but not graded. Only deliverables listed in this document are evaluated.

## Business Context

The operations dashboard is working: the team can browse elevators, see detail panels, search and filter, and the ML pipeline predicts inspection outcomes from historical data. The operations manager is ready for the next step:

"The dashboard gives us a great view of the fleet, but the predictions are stuck in a notebook. I need those risk scores available in real-time when someone looks at an elevator.

The mobile team also wants to build field tools for our inspectors, so they'll need programmatic access to our elevator data, inspections, and risk scores. Right now everything is locked inside the dashboard's HTML pages. We need a proper API that other applications can call.

Once the core data is accessible through the API, I'll also need fleet-level views: how many elevators are at risk overall, what's our inspection pass rate, and which elevators need immediate attention. I want to see that at a glance on the dashboard."

Your team lead adds:

"We're bringing in a Go developer next month to help with backend services. The plan is to build the new API layer in Go while keeping the existing Python frontend running. Set up the Go project now so the new developer has something to build on, and make sure our development standards are documented so they can onboard without guessing at conventions."

Your team's goals for this sprint:

- Organize your project's development standards so they are documented, enforceable, and ready for a new team member
- Define and build a Go JSON API that serves elevator data and risk predictions
- Connect the existing Python/HTMX frontend to the new Go API
- Deploy the Module 3 predictions through the API and display risk indicators on the dashboard
- Add fleet-level endpoints for aggregate statistics and alerts
- Build development workflow tooling (skills, subagents, hooks) to make the team's process repeatable and reliable

## Learning Objectives

By the end of this module, you will be able to:

- Configure Claude Code hooks (PreToolUse, PostToolUse, Stop) for deterministic automation: auto-formatting, file protection, and notifications
- Distinguish between CLAUDE.md (advisory, always loaded), hooks (deterministic, always execute), and skills (load on demand) and choose the right mechanism for each rule
- Build a Go JSON API with proper routing, struct definitions, JSON marshaling, and error handling
- Integrate a Go API with an existing Python/HTMX frontend in a split-service architecture
- Create custom skills (knowledge and action types) and a custom subagent definition
- Design repeatable development workflows as Claude Code skills and use them to build features efficiently
- Operationalize an ML model: pre-compute predictions from a trained pipeline, validate output quality, and serve predictions through an API endpoint

## Prerequisites

### Required Modules
AND-101, AND-102, AND-103

### Starting Point
This module continues the Rocket Elevators project from AND-103. Continue working in the same repository.

Your repository should already contain:

- Python/HTMX server with detail panel, search, status badges, and loading indicators
- Server tests (platform/test_server.py)
- Dashboard specification with interaction specification (docs/dashboard_spec.md)
- Feature engineering specification (docs/feature_engineering_spec.md)
- Feature engineering pipeline and tests (intelligence/feature_engineering.ipynb, intelligence/test_features.py)
- ML pipeline notebook (intelligence/ml_pipeline.ipynb) with trained model
- Feature matrix (data/feature_matrix.csv)
- Merged elevator dataset (data/merged_elevator_data.csv) and all source datasets in /data
- CLAUDE.md with project conventions
- AI Interaction Log (docs/ai-interaction-log.md)

If any of these are missing, revisit AND-103 before starting.

## Module-Wide Requirements

### Understanding AI-Generated Code
This requirement continues from previous modules. Go is a new language for you, and Claude Code will generate most of the boilerplate. Read through the generated code. When something is unfamiliar (goroutines, interfaces, error returns), ask Claude Code to explain it. You must be able to describe what the code does and why it is structured that way.

### AI Interaction Log
Continue the AI Interaction Log from previous modules. Add new entries as you work through this module's tasks. Each entry must identify the module and task (e.g., "AND-104, Task 3").

For each entry, record:

- The module and task (e.g., "AND-104, Task 5")
- The prompt you used (exact or paraphrased)
- What the output got right or wrong
- What you would change next time

This module's theme is extending Claude Code with hooks, skills, and subagents. At least 3 of your entries must document a decision about which extension mechanism to use: why a rule belongs in a hook instead of CLAUDE.md, why you created a skill instead of adding instructions to CLAUDE.md, or how a subagent delegation worked compared to doing the work in your main session.

**Deliverable:** Updated docs/ai-interaction-log.md with at least 6 new entries from this module

**Evaluation Criteria:**

- At least 6 new entries, each identifying the module and task
- Entries span at least three different tasks from this module
- At least 3 entries document a decision about which extension mechanism (hook, skill, subagent, CLAUDE.md) to use and why
- Entries include the prompt used and a specific observation (not just "it worked")

### Labeling Your Work
Every section you add to a notebook, log, or document must start with a markdown header that identifies the module and task:

```
## AND-104 Task 6: Pre-Compute Predictions
```

This applies to all deliverables: notebooks, the AI Interaction Log, reports, and any other files you submit. Work that cannot be traced to a specific module and task cannot be evaluated.

### Improvements and Additional Features
If you make improvements beyond what the tasks require or add features not specified in the requirements (for example, redesigning the dashboard layout, adding API features, or improving data validation), document them in docs/improvements.md. Each entry gets its own header identifying the task it relates to:

```
## AND-104 Task 8: Dashboard Layout Redesign
```

For each improvement or additional feature, describe what you changed or added, where (which files or components), and why. Undocumented improvements and features will not be evaluated.
