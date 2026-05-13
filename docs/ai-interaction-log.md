# AI Interaction Log

This file records prompts submitted to AI tools and the outputs they produced during the development of RocketDash. Each entry notes the date, the tool used, the prompt, and a summary of the result.

---

## Entry 1 — 2026-05-11

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> Generate a README.md that includes: the project name, a one-paragraph description of the project, and a list of the four directories with what each one contains. Also create this file, docs/ai-interaction-log.md.

**What Happened:**
Claude generated `README.md` at the project root with the project name "RocketDash", a one-paragraph description covering the project's purpose (replacing manual spreadsheet workflows with an internal Operations Dashboard), and a table describing the four directories: `data/`, `docs/`, `intelligence/`, and `platform/`. Claude also created this `docs/ai-interaction-log.md` file to track AI-assisted work going forward.

**What I Would Change:**
I would have been more specific with the prompt and described exactly how I wanted the README.md file structured.  Currently there is no title inside of the document.  I would have said at the top of the document write Project: Rocket Dashboard.  Beneath it create a section named Project Description, and describe the Project in one paragraph based on these paramaters. I would have paraphrased the requirements fromm the Business Document.  Next, I would have requested that another section be created named Project Directory with a listing of the directory.  Finally, I would have requested that the fourth section be labeled as Commit and requested that the commit identify the most recent commit in detail.

---

## Entry 2 — 2026-05-13

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> Please update the README file with the following criteria — Title: Rocket Dash. Section 1 - Project Description: Write one paragraph summarizing the project scope and the client's direct request. Section 2 - Directory Listing: Create a listing of the four project directories with descriptions. Section 3 - Commit Description: Provide an explanation of the first commit after the initial commit.

**What Happened:**
Claude read the existing README.md and rewrote it with the requested structure. The title was updated to "Rocket Dash". A Project Description section was written synthesizing the project scope and the client's verbatim request into a single paragraph. A Directory Listing section was added as a table with the four directories (`platform/`, `intelligence/`, `data/`, `docs/`) and their contents. For the Commit Description section, Claude ran `git log` to identify the commits, then read the file added in commit `81b206b` (`docs/ai-workflow-baseline.md`) to accurately summarize what was done. The section was initially placed before the Directory Listing in error; after user correction it was placed in the correct order following the Directory Listing.

**What I Would Change:**
I would not change anything for this prompt.  The output was accurate.

---

## Entry 3 — 2026-05-13

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> Create dashboard_spec.md file in the docs folder. Detailed requirements: Read the operations manager's request in the Business Context section. Identify what they need to see on the dashboard. Write docs/dashboard_spec.md that translates that request into a technical specification. The spec must include: page layout (sidebar, summary metrics, detail table), table columns with data types and display formats, summary cards with how each is calculated. Write in plain English, detailed enough that Claude Code can generate the dashboard without asking clarifying questions.

**What Happened:**
Claude inspected the three relevant dataset files (`license.csv`, `inspection.csv`, `installed.json`) to identify available fields, data types, and distinct values before writing the spec. It confirmed that elevator type information lives in `installed.json` (field: `Device Type`) and that `DeviceStatus` in the same file is the source for active/inactive status. The resulting `docs/dashboard_spec.md` defined: a fixed left sidebar with navigation, a main content area with a page heading, three summary cards (Total Elevators, Active Elevators, Overdue Inspections), and a searchable detail table. Each table column was documented with its source file, source field name, data type, and display format. Join logic across all three data files was specified using the Elevating Device Number as the common key.

**What I Would Change:**

---

## Entry 4 — 2026-05-13

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> I did not see how we approached this challenge in the spec doc: For this project, the operations manager considers an elevator overdue if more than 12 months have passed since its last periodic inspection.

**What Happened:**
Claude updated the Overdue Inspections card definition in `docs/dashboard_spec.md`. The original definition used license expiry date as the overdue criterion, which did not reflect the actual business rule. The updated definition specifies: find the most recent record per elevator in `inspection.csv` where `InspectionType` equals `"ED-Periodic Inspection"`; if that record's `Latest_INSPECTION_Date` is more than 12 months before today, the elevator is overdue. Elevators with no periodic inspection on file are also counted as overdue.

**What I Would Change:**

---

## Entry 5 — 2026-05-13

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> Generate platform/index.html file using Tailwind CSS styling. This is a static prototype of the dashboard, therefore use placeholder data. Invent sample elevator records for the time being.

**What Happened:**
Claude created `platform/index.html` as a fully static prototype of the Fleet Overview dashboard. The file uses Tailwind CSS loaded via CDN. The layout follows the dashboard spec: a fixed left sidebar with the app name and navigation links (Fleet Overview as active, with placeholder links for Inspections, Incidents, and Alterations), a top header, three summary cards (Total Elevators, Active Elevators, Overdue Inspections), and a searchable detail table. Twenty-four invented elevator records were used as placeholder data, covering a range of locations in Toronto and Mississauga, all device types and status values from the real dataset. Status values are displayed as color-coded badges. A live search input filters table rows by Elevator ID or Location as the user types. The file requires no server and can be opened directly in a browser.

**What I Would Change:**