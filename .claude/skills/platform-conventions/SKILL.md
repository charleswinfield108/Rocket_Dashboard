---
name: platform-conventions
description: Platform-layer conventions for the Rocket Elevators dashboard. Covers Flask server startup, the spec-first dashboard workflow, and HTMX endpoint patterns. Apply whenever editing files in platform/, writing Flask endpoints, or modifying the dashboard spec.
triggers:
  - platform/
  - "*.py"
  - "*.html"
---

# Platform Conventions — Rocket Elevators Dashboard

## Flask Server Startup

Start the server with:

```
python3 platform/server.py
```

The dashboard is served at `http://localhost:5000`. Do **not** open `platform/templates/index.html` directly in a browser — it requires the Flask server to be running to serve HTMX endpoints and inject data.

`server.py` is the sole entry point. `platform/templates/index.html` is the only dashboard template.

## Dashboard Change Workflow (Spec-First)

All dashboard changes follow a two-step process:

1. Edit `docs/dashboard_spec.md` — document the intended change in the spec first.
2. Regenerate `platform/templates/index.html` from the spec.

**Never edit `platform/templates/index.html` directly.** Direct HTML edits drift from the spec and are overwritten the next time the page is regenerated.

## HTMX Endpoints

HTMX endpoints return **HTML fragments**, not JSON.

- `/elevators` returns a `<tbody>` fragment for HTMX to swap into the table body.
- Any new HTMX-driven endpoint must return a rendered template fragment via `render_template_string` or a partial template file.
- The HTMX `hx-swap` target on the frontend determines where the fragment is inserted — match the fragment structure to what the swap target expects.

Do not return JSON from endpoints that HTMX will consume. HTMX swaps HTML; a JSON response will appear as raw text in the page.

## Source Data Files

Files under `data/` are source datasets — **do not modify them**. Any derived outputs (merged CSVs, processed files, generated assets) belong in `intelligence/` or `platform/assets/`, not in `data/`.

If a new endpoint or pipeline needs a derived file, write it to the appropriate output directory and load from there — never overwrite or append to the source files in `data/`.

## Generated Data Files

`data/predictions.csv` is a **GENERATED ARTIFACT**. It is produced by running `intelligence/generate_predictions.ipynb` (Restart Kernel and Run All) and must never be hand-edited. To change predictions, modify the notebook and regenerate.
