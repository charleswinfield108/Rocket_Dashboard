# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Rocket Elevators Operations Dashboard — a static prototype dashboard and data analysis workspace for exploring Ontario elevator fleet data.

## Tech Stack

HTML, Tailwind CSS (CDN), vanilla JavaScript, Python 3, pandas, matplotlib, Jupyter notebooks. No build step — `platform/index.html` opens directly in a browser.

## Directories

- `platform/` — frontend (`index.html` is the only page)
- `intelligence/` — Jupyter notebooks
- `data/` — Ontario elevator datasets (do not modify)
- `docs/` — specs and reports

## Data Files (`data/`)

All six datasets share `ElevatingDevicesNumber` / `Elevating devices number` as the join key: `license.csv` (45k rows), `inspection.csv` (143k), `installed.json` (47k), `order.csv` (162k), `altered.json` (32k), `incident.json` (2.4k).

## Conventions

- **Dashboard changes go through the spec first.** Edit `docs/dashboard_spec.md`, then regenerate `platform/index.html`. Do not edit the HTML directly.
- **Run notebooks with:** `/usr/bin/python3 -m jupyter nbconvert --to notebook --execute <path> --output <path> --ExecutePreprocessor.timeout=120`
- Never include `Co-Authored-By: Claude` in commit messages.
