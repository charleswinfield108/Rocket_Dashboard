# Dashboard Specification — Rocket Elevators Fleet Overview

## Purpose

This document describes the layout, content, and data logic for the Rocket Elevators Fleet Overview dashboard. It is intended to be detailed enough for a developer to build the dashboard without needing to ask clarifying questions. The HTML file (`platform/index.html`) must be regenerated from this spec — do not edit the HTML directly.

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

1. **Header bar** — White background with a bottom border. Left side: a four-squares grid icon (`text-gray-700`, `w-6 h-6`) followed by the page title **"Dashboard"** in `text-xl font-semibold`, with a subtext line directly beneath reading "Rocket Dashboard — [Day of Week], [Month] [Day], [Year]" (e.g., "Rocket Dashboard — Thursday, May 14, 2026") at `font-size: 10px` in muted gray (`text-gray-400`). The date in the subtext is **hardcoded as a static string** for this prototype — it does not update automatically. Right side: the search input field (`w-64`) with a magnifying glass icon (`w-4 h-4 text-gray-400`) absolutely positioned inside the left edge of the input, with left padding on the input (`pl-9`) to prevent text overlap.
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

### Card 3 — Inactive Elevators
- **Label:** Inactive Elevators
- **Icon:** X-circle icon, top-right of card. White when selected, orange when unselected.
- **Count color (unselected):** Orange (`text-orange-500`).
- **Value:** Count of elevators where `status !== "Active"`. Computed dynamically.
- **Sub-data:** Operational count (0) · Non-Operational count (same as main count — display for consistency).
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

- **Left:** "Elevator Details" label in small semibold gray text.
- **Center:** Two sort direction buttons displayed side by side, to the left of the sort dropdown:
  - **↑** — sorts the table by the field selected in the dropdown, ascending (alphabetically for text, numerically for IDs, earliest-first for dates)
  - **↓** — sorts the table by the field selected in the dropdown, descending (reverse alphabetical for text, numerically descending for IDs, latest-first for dates)

  Buttons are small (`text-xs`), use a bordered style, and highlight with a dark background and white text when active. Only one button can be active at a time. Clicking an already-active button deactivates it and removes the sort direction. Buttons work in combination with the sort dropdown field, the active card filter, and the search input.

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
| 6 | Last Inspection | `lastInspection` | Date (YYYY-MM-DD) | Gray text |

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

## Search Input

Located in the header bar, right side. Contains a magnifying glass icon inside the left edge of the input. Placeholder text: "Search by ID or location…". Filters table rows in real time — case-insensitive match against Elevator ID or Location. Works in combination with the active card filter and sort.

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
