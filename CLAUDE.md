# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Rocket Elevators Operations Dashboard — a server-driven dashboard and data analysis workspace for exploring Ontario elevator fleet data.

## Tech Stack

HTML, Tailwind CSS (CDN), HTMX, Python 3, Flask, pandas, matplotlib, Jupyter notebooks. The dashboard is served by a Flask server — open via `python3 platform/server.py`, not by opening the HTML file directly.

## Directories

- `platform/` — Flask server (`server.py` is the entry point; `templates/index.html` is the dashboard page)
- `intelligence/` — Jupyter notebooks
- `data/` — Ontario elevator datasets (do not modify)
- `docs/` — specs and reports

## Data Files (`data/`)

All six datasets share `ElevatingDevicesNumber` / `Elevating devices number` as the join key: `license.csv` (45k rows), `inspection.csv` (143k), `installed.json` (47k), `order.csv` (162k), `altered.json` (32k), `incident.json` (2.4k).

## Conventions

- **Dashboard changes go through the spec first.** Edit `docs/dashboard_spec.md`, then regenerate `platform/index.html`. Do not edit the HTML directly.
- **Run notebooks with:** `/usr/bin/python3 -m jupyter nbconvert --to notebook --execute <path> --output <path> --ExecutePreprocessor.timeout=120`
- Never include `Co-Authored-By: Claude` in commit messages.
- **Flask server** is at `platform/server.py`. Start with `python3 platform/server.py`. The dashboard is served at `http://localhost:5000`.
- **HTMX endpoints return HTML fragments, not JSON.** The `/elevators` endpoint returns a `<tbody>` fragment for HTMX to swap into the page.
