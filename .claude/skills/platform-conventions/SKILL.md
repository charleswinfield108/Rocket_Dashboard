---
description: Platform conventions for Python/Flask/HTMX work in the platform/ directory. Auto-load when editing any file under platform/ — server.py, templates/, test_server.py, or the Go API in platform/api/.
---

# Platform Conventions

Rules that apply when working in the `platform/` directory: the Python/Flask frontend server, HTMX templates, and the Go API service.

---

## Starting the Servers

**Python/Flask frontend**
```bash
python3 platform/server.py
```
- Served at `http://localhost:5000`
- Do **not** open `platform/templates/index.html` directly in a browser — the dashboard requires the Flask server to be running

**Go API** *(added AND-104)*
```bash
cd platform/api && go run .
```
- Served at `http://localhost:8081` by default
- Both servers can run simultaneously; they use different ports

---

## Dashboard Changes — Spec First

1. Edit `docs/dashboard_spec.md` first
2. Then update `platform/templates/index.html`
3. Never edit the HTML directly without a corresponding spec change

---

## HTMX Endpoints Return HTML Fragments

Flask endpoints consumed by HTMX return **HTML fragments**, not JSON.

```python
# Correct — returns a <tbody> fragment for HTMX to swap
@app.route("/elevators")
def elevators():
    return render_template("_elevators_rows.html", data=rows)

# Wrong — HTMX endpoints must not return JSON
@app.route("/elevators")
def elevators():
    return jsonify(rows)
```

The `/elevators` endpoint returns a `<tbody>` fragment for HTMX to swap into the page. JSON responses belong to the Go API on port 8081, not to the Python server.

---

## Generated Data Files

`data/predictions.csv` is a **generated artifact** produced by `intelligence/generate_predictions.ipynb`. Do not edit it manually. To update predictions, re-run the notebook and let it overwrite the file.

---

## Go API Conventions *(AND-104)*

- Module lives in `platform/api/`
- Default port: `8081` (configurable via `PORT` environment variable)
- All responses are `Content-Type: application/json`
- CSV data is loaded into memory at startup — do not re-read files per request
- Error responses follow the shape defined in `docs/api_spec.md`
