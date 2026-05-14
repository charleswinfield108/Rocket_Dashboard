# Dashboard Specification — Rocket Elevators Fleet Overview

## Purpose

This document describes the layout, content, and data logic for the Rocket Elevators Fleet Overview dashboard. It is intended to be detailed enough for a developer to build the dashboard without needing to ask clarifying questions.

---

## Page Layout

The page is divided into two regions: a fixed left sidebar and a main content area to its right.

### Sidebar (left, fixed width)

The sidebar is always visible and contains the navigation menu. It displays the application name ("Rocket Elevators Dashboard") at the top, followed by a vertical list of page links. For this release there is one link: "Dashboard", which is the active/highlighted state by default. The nav link uses a four-squares grid icon to its left. The sidebar is styled to make it clear that more links can be added here in the future.

### Main Content Area (right of sidebar)

The main content area is organized top to bottom as follows:

1. **Header bar** — Spans the full width of the main content area. Left side contains a four-squares grid icon followed by the page title "Dashboard" in bold, with a subtext line directly beneath it reading "Rocket Dashboard — [Day of Week], [Month] [Day], [Year]" (e.g., "Rocket Dashboard — Thursday, May 14, 2026") at 10px font size in a muted gray color. Right side contains the search input for filtering the elevator table.
2. **Summary Cards Row** — Three cards displayed side by side in a single horizontal row.
3. **Table Section** — The full elevator detail table. No search input in this section — search has been moved to the header bar.

---

## Summary Cards

Three cards are displayed side by side. Each card shows a label and a large computed number. All counts are calculated dynamically from the data at load time so that the card values always match what the table filter produces.

### Interactivity

- All three cards are clickable.
- On initial page load, the **Total Elevators** card is highlighted by default.
- The highlighted (selected) card uses a blue background with white text. Unselected cards use a white background with their default text colors.
- Clicking a card filters the detail table to show only the rows that correspond to that card's metric, and highlights that card as selected.
- Only one card can be selected at a time. Selecting a new card deselects the previous one.
- The search input works in combination with the active card filter — the table shows only rows that satisfy both the card filter and the search query simultaneously.

### Card 1 — Total Elevators
- **Label:** Total Elevators
- **Icon:** Building icon, positioned in the top-right corner of the card. White when selected, gray when unselected.
- **Value:** Count of all unique Elevating Device Numbers present in `installed.json`. Computed dynamically at load time.
- **Filter behavior:** Shows all elevators in the table with no status filter applied.

### Card 2 — Active Elevators
- **Label:** Active Elevators
- **Icon:** Check-circle icon, positioned in the top-right corner of the card. White when selected, green when unselected.
- **Value:** Count of records in `installed.json` where the `DeviceStatus` field equals `"Active"` (case-sensitive). Computed dynamically at load time.
- **Filter behavior:** Filters the table to show only elevators where `DeviceStatus` equals `"Active"`.

### Card 3 — Overdue Inspections
- **Label:** Overdue Inspections
- **Icon:** Clock icon, positioned in the top-right corner of the card. White when selected, red when unselected.
- **Value:** Count of elevators where more than 12 months have passed since their last periodic inspection. To calculate: for each elevator, find the most recent record in `inspection.csv` where `InspectionType` equals `"ED-Periodic Inspection"`. If that record's `Latest_INSPECTION_Date` is more than 12 months before today's date, the elevator is considered overdue. Elevators with no periodic inspection record on file are also counted as overdue. Parse `Latest_INSPECTION_Date` from `M/D/YYYY` format before comparing. Computed dynamically at load time.
- **Filter behavior:** Filters the table to show only elevators whose last periodic inspection date is more than 12 months before today.

---

## Detail Table

### Search Input

A single text input field is displayed above the table with placeholder text "Search by ID or location…". As the user types, the table rows are filtered in real time to show only rows where the Elevator ID or Location contains the typed string (case-insensitive match).

### Table Columns

The table has one row per elevator. Each row is built by joining three data sources on `Elevating Device Number`:

- Primary source: `installed.json` (field name: `Elevating devices number`)
- License data: `license.csv` (field name: `ElevatingDevicesNumber`)
- Inspection data: `inspection.csv` (field name: `ElevatingDevicesNumber`) — use the record with the most recent `Latest_INSPECTION_Date` for each elevator

| Column | Label | Source File | Source Field | Data Type | Display Format |
|---|---|---|---|---|---|
| 1 | Elevator ID | installed.json | `Elevating devices number` | Number | Display as a plain integer, no formatting |
| 2 | Location | installed.json | `Location of Device` | Text | Display as-is |
| 3 | Type | installed.json | `Device Type` | Text | Display as-is (e.g., "Passenger Elevator", "Freight Elevator") |
| 4 | Status | installed.json | `DeviceStatus` | Text | Display as-is (e.g., "Active", "Inactive", "TSSA Shutdown") |
| 5 | License Expiry | license.csv | `LICENSEEXPIRYDATE` | Date | Parse from `DD-Mon-YY` format and display as `YYYY-MM-DD` |
| 6 | Last Inspection | inspection.csv | `Latest_INSPECTION_Date` | Date | Parse from `M/D/YYYY` format and display as `YYYY-MM-DD`. If no inspection record exists for the elevator, display `—` |

### Table Behavior

- The table displays all elevators by default (no pre-applied filters other than a live search if the user has typed).
- There is no pagination for this prototype; all matching rows are shown.
- Columns are not required to be sortable for this release.

---

## Data Sources Summary

| File | Location | Join Key |
|---|---|---|
| `installed.json` | `data/installed.json` | `Elevating devices number` |
| `license.csv` | `data/license.csv` | `ElevatingDevicesNumber` |
| `inspection.csv` | `data/inspection.csv` | `ElevatingDevicesNumber` |

When joining, use the Elevating Device Number as the common key across all three files. For inspections, select the single most recent record per device based on `Latest_INSPECTION_Date`.

---

## Related Deliverables

### License Dataset Exploration (Prerequisite)

Before dashboard development begins, the team must complete an initial exploration of the license dataset to confirm the data is usable. This work is a prerequisite — if the data is found to be incomplete or unreliable, the dashboard scope may need to be adjusted.

**Goal:** Confirm that `data/license.csv` is structured, complete, and clean enough to power the dashboard.

**Expected output:** A notebook or script in `intelligence/` that addresses the following questions:
- How many records are in the dataset, and how many unique elevators does it cover?
- Are there missing or null values in the key fields used by the dashboard (`ElevatingDevicesNumber`, `LICENSESTATUS`, `LICENSEEXPIRYDATE`, `LocationoftheElevatingDevice`)?
- What is the distribution of `LICENSESTATUS` values (e.g., how many are ACTIVE vs. EXPIRED vs. other statuses)?
- Are there any duplicate Elevating Device Numbers, and if so, how should duplicates be handled?
- Are the date values in `LICENSEEXPIRYDATE` consistently formatted and parseable?

**Success criteria:** The exploration confirms that the key fields are sufficiently complete and consistent to display meaningful data in the dashboard. Any anomalies found should be noted in the notebook with a recommended handling approach.
