# Dashboard Specification — Rocket Elevators Fleet Overview

## Purpose

This document describes the layout, content, and data logic for the Rocket Elevators Fleet Overview dashboard. It is intended to be detailed enough for a developer to build the dashboard without needing to ask clarifying questions. The HTML file (`platform/index.html`) must be regenerated from this spec — do not edit the HTML directly.

---

## Design Philosophy

The dashboard should feel like a premium enterprise product — comparable to Linear, Stripe, or Vercel — not a generic admin panel. Every design decision should serve readability and glanceability first.

### Visual Hierarchy
- Information should be scannable in under three seconds. The most critical metrics (card counts) must be the largest and most visually dominant elements on the page.
- Use size, weight, and color intentionally to guide the eye: large bold counts → labeled card titles → supporting sub-data → table rows.
- Avoid decorative elements that compete with data.

### Color
- Use a restrained accent palette. The brand red (`red-600`) is reserved for the active sidebar nav item and critical states (overdue, expired). It should not appear in neutral UI chrome.
- Status colors (green, orange, red, purple) appear only in summary card counts and table badges — not in backgrounds, borders, or headers.
- The body background uses a very light gray (`gray-50` or `gray-100`) to give cards visual lift without high contrast.
- Dark text on light surfaces for primary data; muted gray for labels and secondary text.

### Depth and Elevation
- Summary cards and the table container use a soft box shadow (`shadow-sm` or `shadow`) with a white background to appear elevated above the page background.
- No harsh borders on cards — use shadow for separation instead of thick outlines. A single thin border (`border border-gray-200`) is acceptable as a subtle edge.
- Avoid stacked shadows or multiple border layers on the same element.

### Spacing and Layout
- Use consistent modular spacing throughout (`gap-5` between cards, `px-8 py-6` for the main content padding, `px-5 py-3` for table cells).
- Card interiors use generous padding so numbers breathe — counts should never feel cramped.
- Thin horizontal dividers (`border-gray-100` or `divide-gray-100`) separate table rows; they should recede visually, not draw attention.

### Typography
- Primary data (counts, IDs, dates) uses `font-mono` or a clean sans-serif with consistent sizing.
- Card counts are the typographic focal point: `text-4xl` or larger, `font-bold`.
- Labels and column headers use `text-xs` or `text-sm` in uppercase or muted gray to create visual separation from data.
- No decorative fonts, no all-caps body text.

### Interactivity
- Interactive elements (cards, buttons, rows) use subtle hover states (`hover:bg-gray-50`, `hover:shadow-md`) — enough to communicate affordance without animation-heavy transitions.
- The active card selection uses a solid fill color (blue) to clearly indicate state; all other cards revert to white.
- Focus rings use the brand red to maintain color consistency.

---

## Server Architecture

The dashboard is no longer served as a static file. It is served by a Python Flask server located at `platform/server.py`.

- The server loads `platform/elevator_fleet.csv` on startup. This file contains cleaned license data prepared by `platform/prepare_data.py`.
- The main dashboard page is served at `/`.
- All table interactivity is handled by HTMX. The server exposes endpoints that return HTML fragments for HTMX to swap into the page — they do not return JSON.
- There is no custom JavaScript for filtering or sorting. All dynamic behavior is driven exclusively by HTMX attributes (`hx-get`, `hx-target`, `hx-swap`).

---

## Page Layout

The page is divided into two regions: a fixed left sidebar and a main content area to its right. The full page height is fixed to the viewport with no body scroll; the main content area scrolls independently.

### Sidebar (left, fixed width `w-56` / 224px)

The sidebar is always visible and does not scroll (`flex-shrink-0`). It has a dark background (`bg-gray-900`). At the top is the application name "Rocket Elevators" in bold white text (`text-lg font-bold`), separated from the nav links by a bottom border (`border-gray-700`).

Navigation links are listed vertically with a small gap between each. For this release there is one active link: **Dashboard**, highlighted with a red background (`bg-red-600`) and white text, using a **four-squares grid icon** to its left. Below it are three placeholder links in muted gray (`text-gray-400`) that highlight on hover:
- **Inspections** — use a table/grid chart icon
- **Incidents** — use an alert/warning circle icon
- **Alterations** — use a pencil/edit icon

Placeholder links are not functional in this prototype.

At the very bottom of the sidebar is a version label "v1.0 — Prototype" in `text-xs text-gray-500`, separated from the nav area by a top border (`border-gray-700`).

**Focus ring color for all inputs:** `focus:ring-red-500` (matches the brand red used in the sidebar active state).

### Main Content Area (right of sidebar)

The main content area is organized top to bottom:

1. **Header bar** — White background with a bottom border. Left side: a four-squares grid icon (`text-gray-700`, `w-6 h-6`) followed by the page title **"Dashboard"** in `text-xl font-semibold`, with a subtext line directly beneath reading "Rocket Dashboard — [Day of Week], [Month] [Day], [Year]" at `font-size: 10px` in muted gray (`text-gray-400`). The date is **generated dynamically at load time** using JavaScript's `new Date()` with `toLocaleDateString('en-CA', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })` — it must not be a hardcoded string. Right side: the search input field (`w-64`) with a magnifying glass icon (`w-4 h-4 text-gray-400`) absolutely positioned inside the left edge of the input, with left padding on the input (`pl-9`) to prevent text overlap.
2. **Summary Cards Grid** — Five cards arranged in a 3-column CSS grid (see Summary Cards section for full layout).
3. **Table Section** — White card containing the Elevator Details table with a sort dropdown in its header.

---

## Summary Cards

Five summary cards are arranged in a **3-column CSS grid** as follows:

```
| Total Elevators (spans 2 rows) | Active Elevators    | Inactive Elevators |
|                                | Overdue Inspections | Expired Licences   |
```

- **Column 1:** Total Elevators card, spanning 2 grid rows (`row-span-2`). Uses `flex flex-col justify-between` so the label sits at the top and the count at the bottom.
- **Columns 2–3, Row 1:** Active Elevators and Inactive Elevators side by side.
- **Columns 2–3, Row 2:** Overdue Inspections and Expired Licences side by side.

All counts are computed dynamically from the data at load time so card values always match the table filter output.

### Interactivity

- All five cards are clickable.
- On initial page load, the **Total Elevators** card is highlighted by default.
- The selected card uses a blue background (`bg-blue-500`) with white text and a white icon. Unselected cards use a white background with their default label, count, and icon colors.
- When selected, the icon turns white. When unselected it returns to its default color.
- Only one card can be selected at a time.
- Clicking a card filters the detail table to show only the rows matching that card's metric.
- The search input and sort dropdown work in combination with the active card filter simultaneously.

### Sub-data (all cards)

Each card displays a secondary line of data below the main count, showing the operational breakdown of that card's subset. The format is:

> **X Operational · Y Non-Operational**

Where:
- **X Operational** = count of elevators in that card's filtered set where `status === "Active"`
- **Y Non-Operational** = count of elevators in that card's filtered set where `status !== "Active"`

This sub-data is displayed in small text (`text-xs`) beneath the main count number. When a card is selected (blue), the sub-data text is white. When unselected, it is muted gray (`text-gray-400`).

### Card 1 — Total Elevators
- **Label:** Total Elevators
- **Icon:** Building icon, top-right of card. White when selected, gray when unselected.
- **Count size:** `text-6xl` (larger than the other cards to fill the double-height space).
- **Value:** Count of all records in the placeholder data array. Computed dynamically.
- **Sub-data:** Operational count and Non-Operational count across all elevators.
- **Filter behavior:** No filter — shows all elevators.
- **Default state:** Selected (blue) on page load.

### Card 2 — Active Elevators
- **Label:** Active Elevators
- **Icon:** Check-circle icon, top-right of card. White when selected, green when unselected.
- **Count color (unselected):** Green (`text-green-600`).
- **Value:** Count of elevators where `status === "Active"`. Computed dynamically.
- **Sub-data:** Operational count (same as main count) · Non-Operational count (0, since all are active — display regardless for consistency).
- **Filter behavior:** Filters table to elevators where `status === "Active"`.

### Card 3 — Non-Active Elevators
- **Label:** Non-Active Elevators
- **Icon:** X-circle icon, top-right of card. White when selected, orange when unselected.
- **Count color (unselected):** Orange (`text-orange-500`).
- **Value:** Count of elevators where `status !== "Active"`. Computed dynamically.
- **Sub-data:** A breakdown of distinct non-active statuses and their counts, displayed as a comma-separated list (e.g., `2 TSSA Shutdown · 1 Customer Shutdown · 1 Undergoing Major Alt`). Only statuses that are present in the current dataset are shown. This replaces the Operational/Non-Operational format used on other cards.
- **Filter behavior:** Filters table to elevators where `status !== "Active"`.

### Card 4 — Overdue Inspections
- **Label:** Overdue Inspections
- **Icon:** Clock icon, top-right of card. White when selected, red when unselected.
- **Count color (unselected):** Red (`text-red-600`).
- **Value:** Count of elevators whose `lastInspection` date is more than 12 months before today. Computed dynamically.
- **Sub-data:** Of the overdue elevators, how many are Operational · how many are Non-Operational.
- **Filter behavior:** Filters table to elevators where `lastInspection` is more than 12 months before today.

### Card 5 — Expired Licences
- **Label:** Expired Licences
- **Icon:** Ban/slash-circle icon, top-right of card. White when selected, purple when unselected.
- **Count color (unselected):** Purple (`text-purple-600`).
- **Value:** Count of elevators where `licenseExpiry` date is before today. Computed dynamically.
- **Sub-data:** Of the expired-licence elevators, how many are Operational · how many are Non-Operational.
- **Filter behavior:** Filters table to elevators where `licenseExpiry` is before today.

---

## Detail Table

### Table Header Bar

The table is contained in a white rounded card. Its header bar is a single flex row with three regions:

- **Left:** "Elevator Details" label in small semibold gray text, followed by a results count in muted gray (`text-xs text-gray-400`) showing the number of rows currently displayed vs. total records — format: `"Showing X of Y elevators"`. This count updates any time the card filter, search, or sort changes.
- **Center:** Two sort direction buttons displayed side by side, to the left of the sort dropdown:
  - **↑** — sorts the table by the field selected in the dropdown, ascending (alphabetically for text, numerically for IDs, earliest-first for dates)
  - **↓** — sorts the table by the field selected in the dropdown, descending (reverse alphabetical for text, numerically descending for IDs, latest-first for dates)

  Buttons are small (`text-xs`), use a bordered style, and highlight with a dark background and white text when active. Only one button can be active at a time. Clicking an already-active button deactivates it and removes the sort direction. **When the sort dropdown field changes, the active sort direction button resets to inactive.** Buttons work in combination with the sort dropdown field, the active card filter, and the search input.

- **Right:** A "Sort by…" dropdown. Selecting a field determines which column the direction buttons act on. Options: Elevator ID, Location, Type, Status, License Expiry, Last Inspection. Sorting works in combination with the active card filter and search.

### Table Columns

One row per elevator. Data is placeholder — hardcoded JavaScript array of elevator objects with these fields: `id`, `location`, `type`, `status`, `licenseExpiry` (YYYY-MM-DD), `lastInspection` (YYYY-MM-DD).

| Column | Label | Field | Data Type | Display Notes |
|---|---|---|---|---|
| 1 | Elevator ID | `id` | Number | Monospace font |
| 2 | Location | `location` | Text | Display as-is |
| 3 | Type | `type` | Text | Display as-is |
| 4 | Status | `status` | Text | Displayed as a colored pill/badge (see Status Badge Colors) |
| 5 | License Expiry | `licenseExpiry` | Date (YYYY-MM-DD) | Red bold text if date is before today; gray text otherwise |
| 6 | Last Inspection | `lastInspection` | Date (YYYY-MM-DD) | Red bold text if date is more than 12 months before today (overdue); gray text otherwise |

### Status Badge Colors

| Status | Badge Style |
|---|---|
| Active | Green background, green text |
| Inactive | Gray background, gray text |
| TSSA Shutdown | Red background, red text |
| Customer Shutdown | Orange background, orange text |
| Undergoing Major Alt | Yellow background, yellow text |

### Table Behavior

- All rows are shown by default (Total Elevators card selected, no search query).
- Filtering by card, search, and sort all apply simultaneously.
- No pagination — all matching rows are shown.
- Rows have a subtle hover background.
- If no rows match the active filters, display a "No elevators match your search." message centered below the table headers.

---

## Filters and Sorting

### Status Filter

A dropdown in the table header bar that filters the table by Device Status. Options: **All**, **Active**, **TSSA Shutdown**, **Customer Shutdown**, **Undergoing Major Alt**. Selecting a value sends a request to the server using `hx-get="/elevators?status=<value>"`, targets the table body, and swaps in the returned HTML fragment. Selecting "All" removes the status filter and returns all rows.

### City Filter

A dropdown in the table header bar that filters the table by city. City is extracted from the Location field as the token immediately before the province code. Options are populated from the distinct cities present in `platform/elevator_fleet.csv`, plus an "All Cities" option. Selecting a value sends a request using `hx-get="/elevators?city=<value>"`, targets the table body, and swaps in the returned HTML fragment.

### Sortable Columns

The **Elevator ID** and **License Expiry Date** column headers are clickable. Clicking a header sorts the table by that column ascending. Clicking the same header again reverses the sort to descending. Sort state is passed to the server as query string parameters (e.g., `sort=id&order=asc`). The server applies all active filter and sort parameters together in a single request and returns the updated table fragment.

### Combined Behavior

All filters and sorting operate simultaneously. Every HTMX request to `/elevators` carries the full current state — active status filter, active city filter, and active sort — as query parameters. The server applies all parameters and returns the appropriate filtered, sorted table fragment. The "Showing X of Y elevators" count in the table header is included in every fragment response and updates automatically on each swap.

---

## Search Input

Located in the header bar, right side. Contains a magnifying glass icon inside the left edge of the input. Placeholder text: "Search by ID, location, type, or status…". Filters table rows in real time — case-insensitive match against Elevator ID, Location, Type, and Status. Works in combination with the active card filter and sort.

---

## Placeholder Data

The prototype uses a hardcoded array of 24 invented elevator records covering locations in Toronto, Mississauga, and Etobicoke. Records include a mix of all five `DeviceStatus` values, multiple `Device Type` values, and a spread of `licenseExpiry` and `lastInspection` dates — some expired and some overdue — to demonstrate all card filters and the red licence expiry highlighting.

---

## Data Sources Summary (for future real-data integration)

| File | Location | Join Key |
|---|---|---|
| `installed.json` | `data/installed.json` | `Elevating devices number` |
| `license.csv` | `data/license.csv` | `ElevatingDevicesNumber` |
| `inspection.csv` | `data/inspection.csv` | `ElevatingDevicesNumber` |

When integrating real data, join all three files on Elevating Device Number. For inspections, use the most recent `Latest_INSPECTION_Date` per device.

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

---

## Data Model

*Added: 2026-05-18*

The dashboard operates on an **Elevator** entity assembled by joining three source datasets on `ElevatingDevicesNumber`. Each row in the detail table represents one physical elevator device.

| Field | Data Type | Source Dataset | Source Column | Description |
|---|---|---|---|---|
| Elevator ID | Number | `license.csv` / `installed.json` | `ElevatingDevicesNumber` / `Elevating devices number` | Unique permanent identifier assigned to each physical elevator device. Primary join key across all datasets. |
| Location | Text | `license.csv` | `LocationoftheElevatingDevice` | Full address string including street, city, postal code, province, and country. City/region is extracted as the token before the province code. |
| Equipment Type | Text | `installed.json` | `Device Type` | Category of elevating device (e.g., Passenger Elevator, Freight Elevator, LULA Elevator, Observation Elevator). |
| Device Status | Text | `installed.json` | `DeviceStatus` | Current operational status assigned by TSSA (e.g., Active, TSSA Shutdown, Customer Shutdown, Undergoing Major Alt). |
| License Status | Text | `license.csv` | `LICENSESTATUS` | Administrative licence state (e.g., ACTIVE, PENDING_RENEWAL). Distinct from Device Status — an elevator can be physically Active but have a licence that is PENDING_RENEWAL. |
| License Expiry Date | Date | `license.csv` | `LICENSEEXPIRYDATE` | Date the operating licence expires. Source format: `DD-MMM-YY` (e.g., `28-Apr-17`). Display format: `YYYY-MM-DD`. |
| Last Inspection Date | Date | `inspection.csv` | `Latest_INSPECTION_Date` | Date of the most recent periodic inspection for this device. Derived by selecting the latest record per `ElevatingDevicesNumber`. |
| Last Inspection Outcome | Text | `inspection.csv` | `InspectionOutcome` | Result of the most recent inspection (e.g., Satisfactory, Unsatisfactory, Conditional Pass). Sourced from the same record as Last Inspection Date. |

> **Note:** License Status is used by the summary card filters but is not displayed as a standalone table column — Device Status is shown instead, as it reflects physical operability. Last Inspection Outcome is a data model field not currently in the table; add it to the Table Columns section if the operations manager needs it visible at a glance.

---

## AND-103 Task 1: Interaction Specification

*Added: 2026-05-28*

---

### Interaction 1: Elevator Detail Panel

**Outcomes**
When a user clicks any row in the fleet table, a side panel opens showing that elevator's complete record. The user can see: inspection history (total count, date and outcome for each inspection), incident count with expandable detail (date and results per incident), alteration count with expandable detail (date, type, and status per alteration), and current device status. The user cannot currently see this information without cross-referencing three separate views; after this interaction is built, everything is available in one panel without leaving the dashboard.

**Scope Boundaries**
- Inspection history: full record from `data/inspection.csv` — not limited to the most recent entry in the merged CSV
- Incidents: full record from `data/incident.json` filtered by elevator ID; count shown with expandable detail (date, results)
- Alterations: full record from `data/altered.json` filtered by elevator ID; count shown with expandable detail (date, type, status)
- Current status, location, and equipment type: read from `data/merged_elevator_data.csv` (already loaded in memory at server startup)
- One panel open at a time — opening a new elevator replaces the current panel
- Style polish (colors, spacing refinement) is out of scope for this iteration; functionality is the priority

**Constraints**
- All panel loading must use HTMX (`hx-get`, `hx-target`, `hx-swap`) — no custom JavaScript fetch calls
- No full page reload when opening, updating, or closing the panel
- Only one detail panel open at a time; clicking a new row replaces the current panel content
- Server response must return under 500ms; source files are read per request and filtered by elevator ID
- Panel response must be an HTML fragment, consistent with the existing `/elevators` endpoint pattern

**Prior Decisions**
- `data/merged_elevator_data.csv` is loaded into memory on server startup; it contains one row per elevator with static fields (location, equipment type, device status, alteration count, most recent inspection only) — it does not contain full history
- Full inspection history, incident records, and alteration records must be read from their source files (`inspection.csv`, `incident.json`, `altered.json`) per request, filtered by `ElevatingDevicesNumber`
- The existing `/elevators` endpoint returns a `<tbody>` HTML fragment; the new `/elevator/{id}` endpoint follows the same pattern — HTML fragment, not JSON
- The Jinja2 template already structures the page; a `#detail-panel` container must be added to the layout

**Task Breakdown**
1. Add a `#detail-panel` container to the page layout in `platform/templates/index.html`
2. Add `hx-get="/elevator/{id}"`, `hx-target="#detail-panel"`, `hx-swap="innerHTML"` to each table row
3. Build the `GET /elevator/{id}` endpoint in `platform/server.py` — reads static info from the merged CSV and full history from source files, returns an HTML fragment
4. Add basic panel structure: sections for Inspections, Incidents, Alterations with a close button (style polish deferred)

**Verification Criteria**
- Clicking a row loads that specific elevator's data — not another elevator's
- Inspection count in the panel matches the actual number of records in `inspection.csv` for that elevator ID
- Requesting a non-existent elevator ID returns HTTP 404
- Clicking a different row while the panel is open replaces the panel content with the new elevator's data
- The panel can be closed without a page reload
- No custom JavaScript is used to load or update the panel

---

### Interaction 2: Filter and Search

**Outcomes**
The user can type in a search box to filter the table by elevator ID or location. Search works simultaneously with the existing status and city dropdown filters — all active filters narrow the results together. Typing 2 or more characters triggers a filtered table update; clearing the search box returns the table to showing all results for the active dropdown state.

**Scope Boundaries**
- Search matches against elevator ID and location only — case-insensitive, partial match
- Search does not match against equipment type, license status, device status, or inspection outcome — the dropdowns handle those fields
- Search and dropdowns always combine: results must satisfy both the search term and any active dropdown values simultaneously
- No multi-field search syntax (e.g., no `id:123 city:Toronto` — one plain text input only)

**Constraints**
- 300ms debounce — a request fires 300ms after the user stops typing, not on every keystroke (value is adjustable during testing)
- Minimum 2 characters — the server ignores the `q` parameter if fewer than 2 characters are provided; no request is sent for 0 or 1 character
- Clearing the search box (0 characters) reverts the table to dropdown-only filtered results
- HTMX only — search triggers `hx-get="/elevators"` with the `q` parameter included alongside all active filter values; no custom JS fetch calls

**Prior Decisions**
- The search input already exists in `platform/templates/index.html` with `hx-get="/elevators"`, `hx-trigger="input changed delay:300ms"`, `hx-include="#filters"`
- The `/elevators` endpoint already accepts a `q` parameter and currently matches against elevator ID, location, license status, and device type
- Required changes: restrict the `q` filter to elevator ID and location only; add a server-side check to ignore `q` values shorter than 2 characters

**Task Breakdown**
1. Update the `/elevators` endpoint in `platform/server.py` — restrict `q` filtering to `elevator_id` and `location` columns only
2. Add a 2-character minimum check in the endpoint — if `len(q) < 2`, treat `q` as empty
3. Verify the debounce delay is set to 300ms in the template (already in place from Module 2)
4. Test: search + dropdown active together, single character does nothing, clearing search reverts results

**Verification Criteria**
- Typing 2 or more characters filters the table to rows where elevator ID or location contains the search term (case-insensitive)
- Typing 1 character produces no table change and fires no server request
- Clearing the search box returns the table to dropdown-only results
- Search and dropdowns combine — results satisfy both the search term and any active dropdown values simultaneously
- A search term that matches no rows shows the "No elevators match your filters" message
- The table does not update on every keystroke — the 300ms debounce delay is visible

---

### Interaction 3: Sort Behavior

**Outcomes**
The table loads pre-sorted by License Expiry Date ascending — the most urgent elevators appear at the top without any user action. Three columns are sortable: Elevator ID, License Expiry Date, and Last Inspection Date. Clicking a column header sorts ascending; clicking the same header again reverses to descending. Sort persists when filters or search change. The sort state is independent of the detail panel.

**Scope Boundaries**
- Sortable columns: Elevator ID, License Expiry Date, Last Inspection Date only
- Non-sortable columns: Location, Equipment Type, Device Status, License Status
- No multi-column sort — only one column is active at a time
- Sort state does not interact with the detail panel — opening or closing the panel does not reset or change the sort

**Constraints**
- HTMX only — clicking a column header sends `hx-get="/elevators"` with `clicked_sort` parameter; no JavaScript sort
- Sort state is carried in hidden fields (`sort-field`, `sort-order`) inside the `#filters` form and included with every HTMX request
- Default sort (License Expiry ascending) must be applied server-side on the initial page load — the table arrives pre-sorted, not sorted after load

**Prior Decisions**
- The `/elevators` endpoint already handles `sort`, `order`, and `clicked_sort` parameters and applies `sort_values` accordingly
- Sort button out-of-band swaps (`hx-swap-oob`) already update button visual state (↑/↓/↕) in the response fragment
- The server already supports sorting by `last_inspection` — only the clickable header button is missing from the template
- Hidden fields `sort-field` and `sort-order` are already in the `#filters` form; their default values must be updated to `license_expiry` and `asc`

**Task Breakdown**
1. Update the `/` route in `platform/server.py` to apply `sort_values("license_expiry", ascending=True)` before rendering the initial page
2. Update the hidden field defaults in `platform/templates/index.html`: `sort-field` value → `"license_expiry"`, `sort-order` value → `"asc"`
3. Add a Last Inspection Date clickable header button to the table in the template, following the same pattern as the Elevator ID and License Expiry buttons
4. Verify sort persists when status filter, city filter, or search is changed
5. Verify opening and closing the detail panel does not affect sort state

**Verification Criteria**
- Page loads with the table already sorted by License Expiry Date ascending — no click required
- Clicking License Expiry Date toggles ascending → descending → ascending on successive clicks
- Clicking a different column header resets to ascending on the new column
- The active sort column header is visually highlighted; inactive columns display ↕
- Applying a status filter, city filter, or search term while sorted preserves the current sort order
- Last Inspection Date column header is clickable and sorts correctly in both directions
- Opening or closing the detail panel does not change the active sort column or direction
- Sort, filters, and search all apply simultaneously in a single server request

---

## AND-105 Task 2: Relational Data Model

This section documents the five-table relational schema that maps the Ontario elevator source files to a PostgreSQL database. The corresponding DDL lives at `platform/api/migrations/001_initial_schema.sql`.

---

### Source File Inventory

Before any schema decisions were made, each source file was inspected for real column names, data types inferred from sampled values, null rates, and uniqueness. Findings relevant to design:

**Shared join key (exact name per file):**

| File | Join key column | Format |
|------|----------------|--------|
| `license.csv` | `ElevatingDevicesNumber` | integer string, e.g. `"10"` |
| `inspection.csv` | `ElevatingDevicesNumber` | integer string |
| `incident.json` | `elevating devices number` | integer |
| `altered.json` | `Elevating Devices Number` | integer |
| `predictions.csv` | `elevator_id` | prefixed string `"EL-00000010"` — strip `EL-` prefix, parse as integer |
| `installed.json` | `Elevating devices number` | integer |

All values join to the same numeric `ElevatingDevicesNumber` domain.

**Redacted columns omitted from schema:**

| Source | Column | Reason |
|--------|--------|--------|
| `license.csv` | `LICENSEHOLDERACCOUNTNUMBER` | 100% literal `"data redacted"` |
| `license.csv` | `BILLINGACCOUNT` | 100% literal `"data redacted"` |
| `installed.json` | `Owner Account Number` | 100% literal `"redacted"` |
| `altered.json` | `Inspection number` | 100% NULL in 31,619 rows |
| `altered.json` | `Alteration contractor name` | 100% NULL in 31,619 rows |

**Orphan child records (child ID not present in `license.csv`):**

| Child file | Orphan count | Total rows | % |
|------------|-------------|------------|---|
| `inspection.csv` | 145 | 40,954 | 0.35% |
| `predictions.csv` | 145 | 40,954 | 0.35% |
| `incident.json` | 1 | 2,446 | 0.04% |
| `altered.json` | 9 | 31,619 | 0.03% |

The 145 orphan inspections and 145 orphan predictions are the **same 145 elevator IDs** — consistent with the existing Go API behaviour that already skips these rows (the AND-104 join-orphan fix).

---

### Table Definitions

#### `elevators`

**Sources:** `data/license.csv` (identity + license columns) and `data/installed.json` (device attributes). Both files share the same join key; the `merged_elevator_data.csv` used by the current Go API is the natural join of these two files. Because device facts (type, class, status, owner) belong to the elevator entity, they are stored in this table rather than a separate one — placing them elsewhere would duplicate the entity.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `INTEGER` | `PRIMARY KEY` | `ElevatingDevicesNumber` — natural PK, see §PK Decisions |
| `license_number` | `TEXT` | `NOT NULL UNIQUE` | `ElevatingDevicesLicenseNumber` |
| `location` | `TEXT` | — | `LocationoftheElevatingDevice` (0.1% null) |
| `license_status` | `TEXT` | `NOT NULL` | `LICENSESTATUS` — 11 distinct values |
| `license_expiry` | `DATE` | — | `LICENSEEXPIRYDATE`; source format `dd-Mon-yy` (e.g. `28-Apr-17`) |
| `license_holder` | `TEXT` | — | `LICENSEHOLDER` |
| `license_holder_address` | `TEXT` | — | `LICENSEHOLDERADDRESS` |
| `billing_customer` | `TEXT` | — | `BILLINGCUSTOMER` |
| `billing_address` | `TEXT` | — | `BILLINGADDRESS` |
| `device_type` | `TEXT` | — | `Device Type` from `installed.json` |
| `device_class` | `TEXT` | — | `Device Class` from `installed.json` |
| `device_status` | `TEXT` | — | `DeviceStatus` from `installed.json` |
| `under_review` | `BOOLEAN` | — | `under review` — `'Y'` → `true`, `'N'` → `false` |
| `owner_name` | `TEXT` | — | `Owner Name` from `installed.json` |
| `owner_address` | `TEXT` | — | `Owner Address` from `installed.json` |

---

#### `inspections`

**Source:** `data/inspection.csv`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `INTEGER` | `PRIMARY KEY` | `InspectionNumber` — natural PK |
| `elevator_id` | `INTEGER` | `NOT NULL REFERENCES elevators(id)` | `ElevatingDevicesNumber` |
| `service_request_number` | `TEXT` | — | `originatingservicerequestnumber` — not unique (multiple inspections share one SR) |
| `customer` | `TEXT` | — | `InspectionCustomer` |
| `inspection_type` | `TEXT` | — | `InspectionType` — 29 distinct values |
| `location` | `TEXT` | — | `InspectionLocation` (0.1% null) |
| `earliest_date` | `DATE` | — | `Earliest_INSPECTION_Date`; source format `M/D/YYYY` |
| `latest_date` | `DATE` | — | `Latest_INSPECTION_Date`; source format `M/D/YYYY` |
| `outcome` | `TEXT` | — | `InspectionOutcome` — 34 distinct values |

---

#### `incidents`

**Source:** `data/incident.json`

The 29 specific injury-type columns and 4 severity summary columns are stored as `SMALLINT` — source values are `0.0`, `1.0`, `2.0`, `3.0` (victim counts). All 33 columns share a 56.6% null rate as a group, indicating they originate from a separate data-entry form not completed for all incidents. They are kept as flat columns (not a sub-table) because the task specifies exactly five tables.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `INTEGER` | `PRIMARY KEY` | `Incident Number` — natural PK |
| `elevator_id` | `INTEGER` | `NOT NULL REFERENCES elevators(id)` | `elevating devices number` |
| `task_number` | `INTEGER` | — | `Task Number` (unique per incident) |
| `category` | `TEXT` | — | `catagory of incident` [sic] — 2 values |
| `incident_summary` | `TEXT` | — | `Incident Summary` — 22 values |
| `date_of_occurrence` | `DATE` | — | `Date Of Occurrence`; format `dd-Mon-yy` |
| `time_of_occurrence` | `TIME` | — | `Time of Occurrence`; format `H:MM:SS AM/PM` |
| `creation_date` | `DATE` | — | `Creation Date`; format `dd-Mon-yy` |
| `root_cause` | `TEXT` | — | `Specific Root Cause` (64.9% null) |
| `narrative` | `TEXT` | — | `Reported occurrence narrative` |
| `inspection_notes` | `TEXT` | — | `Summarized detail of Inspection and tests` (89.4% null) |
| `inspector_conclusion` | `TEXT` | — | `Inspector's Conclusion` (89.4% null) |
| `release` | `TEXT` | — | `release` — all rows = `'yes'` |
| `severity_fatal` | `SMALLINT` | — | `fatal injury` |
| `severity_permanent` | `SMALLINT` | — | `permanent (serious) injury` |
| `severity_minor` | `SMALLINT` | — | `non-permanent (minor) injury` |
| `severity_no_injury` | `SMALLINT` | — | `No Injury` |
| `injury_fatal_victim` | `SMALLINT` | — | `Fatal Injury Victim` |
| `injury_concussion` | `SMALLINT` | — | `Concussion Intracranial Inju` |
| `injury_burns_severe` | `SMALLINT` | — | `Burns Severe` |
| `injury_burns_minor` | `SMALLINT` | — | `Burns Minor` |
| `injury_whiplash` | `SMALLINT` | — | `Whiplash` |
| `injury_spinal` | `SMALLINT` | — | `Spinal Injury` |
| `injury_amputation` | `SMALLINT` | — | `Amputation` |
| `injury_deafness` | `SMALLINT` | — | `Injury Leading Deafness` |
| `injury_heart_attack` | `SMALLINT` | — | `Heart Attack` |
| `injury_fracture_major` | `SMALLINT` | — | `Fracture Major Bone` |
| `injury_eye` | `SMALLINT` | — | `Eye Injury` |
| `injury_electric_severe` | `SMALLINT` | — | `Electric Shock Severe` |
| `injury_electric_minor` | `SMALLINT` | — | `Electric Shock Minor` |
| `injury_dislocation` | `SMALLINT` | — | `Dislocation Limb` |
| `injury_bruise_internal` | `SMALLINT` | — | `Bruise Hemorrhage Interna` |
| `injury_exposure_carcinogen` | `SMALLINT` | — | `Exposure Carcinomatou Poison` |
| `injury_swelling` | `SMALLINT` | — | `Swelling` |
| `injury_sprained` | `SMALLINT` | — | `Sprained Twisted Joints Muscle` |
| `injury_skin_infection` | `SMALLINT` | — | `Skin Infection Irritation` |
| `injury_seizure` | `SMALLINT` | — | `Seizure` |
| `injury_respiratory` | `SMALLINT` | — | `Respiratory Infection Irrita` |
| `injury_poisoning` | `SMALLINT` | — | `Poisoning` |
| `injury_other_internal` | `SMALLINT` | — | `Other Internal Injury` |
| `injury_nausea` | `SMALLINT` | — | `Nausea Dizziness` |
| `injury_laceration_superficial` | `SMALLINT` | — | `Laceration Superficial Cut` |
| `injury_laceration_deep` | `SMALLINT` | — | `Laceration Deep Cut` |
| `injury_fracture_minor` | `SMALLINT` | — | `Fracture Nose Fingers Toes` |
| `injury_external_bruise` | `SMALLINT` | — | `External Bruise` |
| `injury_aches_pains` | `SMALLINT` | — | `Aches Pains` |

---

#### `alterations`

**Source:** `data/altered.json`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `INTEGER` | `PRIMARY KEY` | `originating service request number` — natural PK |
| `elevator_id` | `INTEGER` | `NOT NULL REFERENCES elevators(id)` | `Elevating Devices Number` |
| `customer` | `TEXT` | — | `Alteration Customer` |
| `summary` | `TEXT` | — | `Summary` |
| `location` | `TEXT` | — | `Alteration  Location` (source key has extra space) |
| `alteration_type` | `TEXT` | — | `Alteration Type` — 3 values |
| `status` | `TEXT` | — | `Status of Alteration Request` — 12 values |
| `billing_customer` | `TEXT` | — | `Billing Customer` |

---

#### `predictions`

**Source:** `data/predictions.csv`

One prediction row per elevator; `elevator_id` is simultaneously the natural identifier and the FK to `elevators`. This table's PK is also its only FK.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `elevator_id` | `INTEGER` | `PRIMARY KEY REFERENCES elevators(id)` | Strip `EL-` prefix from source value |
| `predicted_outcome` | `TEXT` | `NOT NULL` | — |
| `confidence` | `NUMERIC(8,6)` | `NOT NULL` | P(predicted_outcome) |
| `risk_score` | `NUMERIC(8,6)` | `NOT NULL` | P("Follow up") |
| `risk_level` | `TEXT` | `NOT NULL` | `high` / `medium` / `low` |
| `model_version` | `TEXT` | `NOT NULL` | — |
| `prediction_date` | `DATE` | `NOT NULL` | ISO 8601 in source |
| `prob_all_orders_resolved` | `NUMERIC(8,6)` | — | — |
| `prob_complete` | `NUMERIC(8,6)` | — | — |
| `prob_dc_follow_up` | `NUMERIC(8,6)` | — | — |
| `prob_fail_initial` | `NUMERIC(8,6)` | — | — |
| `prob_follow_up` | `NUMERIC(8,6)` | — | — |
| `prob_follow_up_initial` | `NUMERIC(8,6)` | — | — |
| `prob_follow_up_major` | `NUMERIC(8,6)` | — | — |
| `prob_follow_up_sub_major` | `NUMERIC(8,6)` | — | — |
| `prob_other` | `NUMERIC(8,6)` | — | — |
| `prob_passed` | `NUMERIC(8,6)` | — | — |
| `prob_passed_major` | `NUMERIC(8,6)` | — | — |
| `prob_shutdown` | `NUMERIC(8,6)` | — | — |
| `prob_unable_to_inspect` | `NUMERIC(8,6)` | — | — |
| `risk_explanation` | `TEXT` | — | **NULL now** — populated in a later task |

---

### Primary Key Decisions

| Table | PK Choice | Evidence |
|-------|-----------|----------|
| `elevators` | Natural — `ElevatingDevicesNumber` | 45,383 rows, 45,383 unique, 0 nulls. Every other table's FK points here. Using it as a natural PK avoids storing a redundant surrogate while preserving the join-key semantics every file already uses. |
| `inspections` | Natural — `InspectionNumber` | 143,181 rows, 143,181 unique, 0 nulls. |
| `incidents` | Natural — `Incident Number` | 2,446 rows, 2,446 unique, 0 nulls. |
| `alterations` | Natural — `originating service request number` | 31,619 rows, 31,619 unique, 0 nulls. |
| `predictions` | Natural — `elevator_id` (stripped integer) | 40,954 rows, 40,954 unique. One prediction per elevator; the stripped integer value equals `ElevatingDevicesNumber`. Using a surrogate would add a column with no information gain since this is a 1:1 relationship keyed on elevator_id. |

Surrogate keys (e.g. `BIGINT GENERATED ALWAYS AS IDENTITY`) were considered and rejected for all five tables because every source natural key was confirmed unique and non-null. Surrogate keys would add overhead without fixing any data quality problem — there are no duplicates to absorb.

---

### Relationships

```
elevators 1 ─────────── ∞ inspections   (via elevators.id = inspections.elevator_id)
elevators 1 ─────────── ∞ incidents     (via elevators.id = incidents.elevator_id)
elevators 1 ─────────── ∞ alterations   (via elevators.id = alterations.elevator_id)
elevators 1 ─────────── 0..1 predictions (via elevators.id = predictions.elevator_id)
```

**Cardinality:**
- One elevator can have many inspections (median ~3, range 0–hundreds).
- One elevator can have many incidents (most have 0; a few have multiple).
- One elevator can have many alterations.
- One elevator has at most one prediction row (predictions.csv has exactly one row per elevator).

**FK policy: STRICT + filter-on-load**

All four child tables use `REFERENCES elevators(id) ON DELETE RESTRICT`.

*Why strict, not deferred or nullable FK:*
The database should enforce referential integrity — a child record with no parent elevator is a data quality problem, not a valid state. Making FK nullable would allow it silently.

*Why RESTRICT, not CASCADE:*
Deleting an elevator record should not silently remove its entire inspection, incident, and alteration history. Preventing the delete until children are removed first forces an explicit decision. In a production workflow, elevator deactivation would be modeled as a status change (`license_status`), not a row delete.

*Handling orphans at load time:*
The 145 inspection/prediction orphans, 1 incident orphan, and 9 alteration orphans will be filtered during data migration with:
```sql
INSERT INTO inspections
  SELECT ... FROM staging_inspections
  WHERE elevator_id IN (SELECT id FROM elevators);
```
This is intentional data loss of less than 0.35% of child rows. The alternative — inserting orphan parent stubs into `elevators` — would pollute the elevator table with records that have no license data. The filter approach is consistent with the existing Go API behaviour, which already skips these rows.

---

### Source-to-Column Mappings

#### elevators

| Source file | Source column | DB column | Transformation |
|-------------|--------------|-----------|----------------|
| `license.csv` | `ElevatingDevicesNumber` | `id` | String → INTEGER |
| `license.csv` | `ElevatingDevicesLicenseNumber` | `license_number` | No transform |
| `license.csv` | `LocationoftheElevatingDevice` | `location` | No transform |
| `license.csv` | `LICENSESTATUS` | `license_status` | No transform |
| `license.csv` | `LICENSEEXPIRYDATE` | `license_expiry` | `dd-Mon-yy` string → DATE (e.g. `28-Apr-17` → `2017-04-28`) |
| `license.csv` | `LICENSEHOLDER` | `license_holder` | No transform |
| `license.csv` | `LICENSEHOLDERADDRESS` | `license_holder_address` | No transform |
| `license.csv` | `BILLINGCUSTOMER` | `billing_customer` | No transform |
| `license.csv` | `BILLINGADDRESS` | `billing_address` | No transform |
| `installed.json` | `Device Type` | `device_type` | No transform |
| `installed.json` | `Device Class` | `device_class` | No transform |
| `installed.json` | `DeviceStatus` | `device_status` | No transform |
| `installed.json` | `under review` | `under_review` | `'Y'` → `true`, `'N'` → `false` |
| `installed.json` | `Owner Name` | `owner_name` | No transform |
| `installed.json` | `Owner Address` | `owner_address` | No transform |

#### inspections

| Source column | DB column | Transformation |
|--------------|-----------|----------------|
| `InspectionNumber` | `id` | String → INTEGER |
| `ElevatingDevicesNumber` | `elevator_id` | String → INTEGER |
| `originatingservicerequestnumber` | `service_request_number` | No transform |
| `InspectionCustomer` | `customer` | No transform |
| `InspectionType` | `inspection_type` | No transform |
| `InspectionLocation` | `location` | No transform |
| `Earliest_INSPECTION_Date` | `earliest_date` | `M/D/YYYY` → DATE (e.g. `1/10/2011` → `2011-01-10`) |
| `Latest_INSPECTION_Date` | `latest_date` | `M/D/YYYY` → DATE |
| `InspectionOutcome` | `outcome` | No transform |

#### incidents

| Source key | DB column | Transformation |
|-----------|-----------|----------------|
| `Incident Number` | `id` | INTEGER (already int in JSON) |
| `elevating devices number` | `elevator_id` | INTEGER (already int) |
| `Task Number` | `task_number` | INTEGER |
| `catagory of incident` | `category` | No transform (preserve source typo in data; column name is correct) |
| `Incident Summary` | `incident_summary` | No transform |
| `Date Of Occurrence` | `date_of_occurrence` | `dd-Mon-yy` → DATE |
| `Time of Occurrence` | `time_of_occurrence` | `H:MM:SS AM/PM` → TIME |
| `Creation Date` | `creation_date` | `dd-Mon-yy` → DATE |
| `Specific Root Cause` | `root_cause` | No transform |
| `Reported occurrence narrative` | `narrative` | No transform |
| `Summarized detail of Inspection and tests` | `inspection_notes` | No transform |
| `Inspector's Conclusion` | `inspector_conclusion` | No transform |
| `release` | `release` | No transform |
| `fatal injury` | `severity_fatal` | `float` → SMALLINT (cast `1.0` → `1`, NULL → NULL) |
| `permanent (serious) injury` | `severity_permanent` | float → SMALLINT |
| `non-permanent (minor) injury` | `severity_minor` | float → SMALLINT |
| `No Injury` | `severity_no_injury` | float → SMALLINT |
| `Fatal Injury Victim` … `Aches Pains` (29 cols) | `injury_fatal_victim` … `injury_aches_pains` | float → SMALLINT; snake_case rename |

#### alterations

| Source key | DB column | Transformation |
|-----------|-----------|----------------|
| `originating service request number` | `id` | INTEGER (already int) |
| `Elevating Devices Number` | `elevator_id` | INTEGER (already int) |
| `Alteration Customer` | `customer` | No transform |
| `Summary` | `summary` | No transform |
| `Alteration  Location` (extra space) | `location` | Strip extra whitespace from key name during load |
| `Alteration Type` | `alteration_type` | No transform |
| `Status of Alteration Request` | `status` | No transform |
| `Billing Customer` | `billing_customer` | No transform |

#### predictions

| Source column | DB column | Transformation |
|--------------|-----------|----------------|
| `elevator_id` (`EL-XXXXXXXX`) | `elevator_id` | Strip `EL-` prefix, parse as INTEGER |
| `predicted_outcome` | `predicted_outcome` | No transform |
| `confidence` | `confidence` | String → NUMERIC(8,6) |
| `risk_score` | `risk_score` | String → NUMERIC(8,6) |
| `risk_level` | `risk_level` | No transform |
| `model_version` | `model_version` | No transform |
| `prediction_date` | `prediction_date` | ISO 8601 string → DATE (already `YYYY-MM-DD`) |
| `prob_all_orders_resolved` … `prob_unable_to_inspect` (13 cols) | same names | String → NUMERIC(8,6) |
| *(no source column)* | `risk_explanation` | Insert as NULL |

---

### Indexes

Indexes are justified by actual query patterns found in `platform/api/handlers.go`:

| Index | Justification |
|-------|--------------|
| `inspections(elevator_id)` | FK column; `handleGetInspections` fetches all rows for one elevator |
| `inspections(elevator_id, latest_date DESC)` | Covers the "most recent inspection" sort in `handleGetInspections` |
| `inspections(outcome)` | `handleFleetStats` groups all inspections by outcome for pass-rate calculation |
| `incidents(elevator_id)` | FK column |
| `alterations(elevator_id)` | FK column |
| `elevators(license_status)` | `handleListElevators` filters by `status` query parameter |
| `predictions(risk_level)` | `handleFleetAlerts` filters `WHERE risk_level = 'high'` |
| `predictions(risk_score DESC)` | `handleFleetAlerts` sorts results descending by risk score |


