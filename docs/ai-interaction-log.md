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
The prompt I submitted generated a good base for  the dashboard. It contained the required elements and delivered exactly what the prompt requested. In terms of additional functionality such as sorting the dashboard can be challenging to navigate. For instance, the client wants to be able to get a snapshot of data by  group such as active, inactive, expired liscence, TSSA Shutdown, and Customer Shutdown. A sort feature will be an excellent  addition.  It was not explained in the prompt and not intuitively administered. In addition Claude generated three summary cards and those cards represent total  elevators, active elevators, and expired liscences.  This is what the client requested but to make the dashboard more interactive the clards cn be clickable and sort the table on click.  Since those are the main pieces of data the client would like to use they should be easily and readily accessible.  Easch summary card only shows the total number of each respective subject. It could be beneficial to add "heads up" data such as 5 Elevators added in the last thirty days, or 5 licences to be added soon.  I am going to refine the prompt and spec doc to be more specific.  In addition I will add specific features to sections individually.  For instance summary cards should be clickable and sort the data in the table respectively.

---

## Entry 6 — 2026-05-14

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> Currently the header reads Fleet Overview. Change Fleet Overview to Dashboard. Underneath the word Dashboard add a small sub text 10px that says Rocket Dashboard Day of the Week (Thursday), Month (May), Current Day (14), Year (2026). The text should be on the left of the dashboard. Add the same icon used in the navigation menu to the left of the word Dashboard. Change the icon in both the navigation menu and header to four squares. Move the search bar currently located on the table to the right side of the dashboard header. Add these specifications to the docs/dashboard_spec.md document.

**What Happened:**
Claude updated `platform/index.html` with all requested changes. The nav item icon was replaced with a four-squares grid icon and its label changed from "Fleet Overview" to "Dashboard". The header was rebuilt as a flex row: the left side now shows the grid icon alongside the "Dashboard" title and a 10px muted subtext reading "Rocket Dashboard — Thursday, May 14, 2026"; the right side holds the search input, relocated from the table section. The table section header was simplified to just the "Elevator Details" label. `docs/dashboard_spec.md` was updated to reflect the new nav label, grid icon usage, header layout, subtext format, and search bar placement.

**Task 2**

**Prompt:**
> Add a magnifying glass inside of the search bar.

**What Happened:**
Claude wrapped the search input in a relative-positioned container and added a magnifying glass SVG icon absolutely positioned on the left interior of the input field. The input padding was adjusted to prevent text from overlapping the icon.

**What I Would Change:**
AI generated exactly what was requested in the prompt.  Typocally search bars have the magnifying glass as an icon and that was not added with the initial prompt, so I added it with a second prompt.  Other than that everything worked perfectly.

---

## Entry 7 — 2026-05-14

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> When the user first logs into the dashboard the Total Elevators Card should be highlighted. Currently, I am not in possession of the brand standard colors but we can use a light shade of blue with white and/or light gray text. All of the summary cards should be clickable and when a specific card is selected it should sort the table accordingly. If active elevators is selected, then only active elevators should be shown in the table.

**What Happened:**
Claude added click interactivity to all three summary cards. On load, the Total Elevators card is highlighted with a blue background and white text as the default selected state. Clicking any card highlights it in blue and filters the detail table to match — Total Elevators shows all records, Active Elevators shows only records with `DeviceStatus = "Active"`, and Overdue Inspections shows only records whose last inspection date is more than 12 months ago. Only one card can be selected at a time. The search bar continues to work in combination with the active card filter.

**Task 2**

**Prompt:**
> Awesome! When I click on Overdue Inspections it shows a total of 7 elevators but the card says that there is 5.

**What Happened:**
Claude identified that the card counts were hardcoded as static values, causing a mismatch with the filter logic. All three card counts were updated to be computed dynamically from the data at load time. The Overdue Inspections card now correctly displays 7, matching the number of rows shown when that card is clicked.

**Task 3**

**Prompt:**
> Update the docs/dashboard_spec.md file to show the behavior required for summary cards.

**What Happened:**
Claude updated the Summary Cards section of `docs/dashboard_spec.md` to document the full interactivity: dynamic count calculation at load time, default selected state for Total Elevators, blue highlight styling for the selected card, single-selection behavior, per-card filter logic, and how the search input works in combination with the active card filter.

**What I Would Change:**

---

## Entry 8 — 2026-05-14

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> I want to update the summary cards to Total Elevators, Operational Elevators, Non-Operational Elevators, Overdue Inspections. Would this conflict with Task 5?

**What Happened:**
Claude explained that the dashboard update and Task 5 operate in completely separate parts of the project — the dashboard lives in `platform/` while Task 5 is a Jupyter notebook in `intelligence/`. No conflict exists. Claude noted that Task 5's classification task will define which license statuses are operational vs. non-operational, which could inform the dashboard cards. Two options were presented: update the dashboard now using best-judgment classifications, or complete Task 5 first to establish data-driven definitions before building the new cards. The user decided to finish dashboard tasks first and drill down on functionality afterward.

**What I Would Change:**

---

## Entry 9 — 2026-05-14

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> Update the summary cards to 4 with the following categories: Total Elevators, Operational Elevators, Non-Operational Elevators, Overdue Inspections.

**What Happened:**
Claude updated the summary cards from 3 to 4, changing the grid to `grid-cols-4`. The "Active Elevators" card was renamed to "Operational Elevators" (filtering to `DeviceStatus === "Active"`). A new "Non-Operational Elevators" card was added filtering to all elevators where `DeviceStatus` is not "Active", using an orange x-circle icon. All card counts and filter logic were updated accordingly.

**Task 2**

**Prompt:**
> Add one more card that shows expired licence. Use a 3 column grid format and make the height of Total Elevators match two rows. Stack the remaining cards two on top of two.

**What Happened:**
Claude added an "Expired Licences" card with a purple ban icon, filtering to elevators where `licenseExpiry` is before today. The grid was restructured to 3 columns with Total Elevators spanning 2 rows on the left, and the four remaining cards arranged in a 2×2 grid in columns 2 and 3. The Total Elevators count number was increased to `text-6xl` to fill the taller card height. The `selectCard` function was updated to preserve `row-span-2` and `flex flex-col justify-between` classes on the Total Elevators card across state changes.

**Task 3**

**Prompt:**
> Add a sorting feature to the Elevator Details table. Place it on the right side of the table header as a dropdown. Add all filterable labels to the options.

**What Happened:**
Claude added a "Sort by…" dropdown to the right side of the Elevator Details table header. Initial implementation included ascending and descending options per column, which was simplified after user feedback to just the six column labels (Elevator ID, Location, Type, Status, License Expiry, Last Inspection). Selecting a field sorts the table ascending by that field, in combination with the active card filter and search.

**Task 4**

**Prompt:**
> In the license expiry column highlight the expired licenses in red.

**What Happened:**
Claude updated the `renderTable` function to check each elevator's `licenseExpiry` date against today. Expired dates are rendered in red bold text; valid dates remain in the default gray.

**What I Would Change:**