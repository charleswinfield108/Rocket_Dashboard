# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Rocket Elevators Operations Dashboard — a server-driven dashboard and data analysis workspace for exploring Ontario elevator fleet data.

## Tech Stack

HTML, Tailwind CSS (CDN), HTMX, Python 3, Flask, pandas, matplotlib, Jupyter notebooks. Go (platform/api/).

## Directories

- `platform/` — Flask server (`server.py` is the entry point; `templates/index.html` is the dashboard page) and Go API (`api/`)
- `intelligence/` — Jupyter notebooks
- `data/` — Ontario elevator datasets (do not modify)
- `docs/` — specs and reports

## Data Files (`data/`)

All six datasets share `ElevatingDevicesNumber` / `Elevating devices number` as the join key: `license.csv` (45k rows), `inspection.csv` (143k), `installed.json` (47k), `order.csv` (162k), `altered.json` (32k), `incident.json` (2.4k).

## Conventions

- **Run notebooks with:** `cd intelligence && /usr/bin/python3 -m jupyter nbconvert --to notebook --execute <notebook>.ipynb --output <notebook>.ipynb --ExecutePreprocessor.timeout=120` — always `cd` into `intelligence/` first and pass a filename-only `--output`. Passing a path like `intelligence/etl_pipeline.ipynb` as `--output` causes nbconvert to double the directory prefix.
- Never include `Co-Authored-By: Claude` in commit messages.
- Platform-specific rules (Flask, HTMX, dashboard spec workflow) are in `.claude/skills/platform-conventions/SKILL.md`.
