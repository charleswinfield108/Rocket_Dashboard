# RocketDash

RocketDash is an internal Operations Dashboard built for Rocket Elevators to replace the manual spreadsheet-based workflows currently used by the operations team. The system consolidates years of elevator data collected across Ontario — covering licenses, inspections, incidents, and alterations — into a single, accessible interface. The initial release gives operations managers a fleet-level summary (total elevators, active units, overdue inspections) alongside a searchable table of every elevator's key details, including location, type, status, license expiry, and last inspection date. The project is structured to grow: a persistent sidebar supports future page additions, and the underlying data exploration confirms the dataset is clean and ready for production use.

## Directories

| Directory | Contents |
|-----------|----------|
| `data/` | Raw source datasets exported from Rocket Elevators' records systems, including CSV and JSON files for licenses, inspections, incidents, alterations, installations, and orders. |
| `docs/` | Project documentation, including stakeholder artifacts, AI interaction logs, and any written deliverables produced during development. |
| `intelligence/` | Data exploration and analysis work — notebooks, scripts, and outputs used to validate the datasets and surface insights before the dashboard is built. |
| `platform/` | The dashboard application itself — all front-end and back-end source code for the Operations Dashboard UI. |
