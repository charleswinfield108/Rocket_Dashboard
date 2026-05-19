# AND-101 Generative AI Fundamentals

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
I would have read the business requirements document more thoroughly before writing this prompt. The spec was generated without the 12-month overdue inspection rule, which required a separate correction in Entry 4. Including all business rules in the initial prompt — rather than discovering omissions after the fact — would have produced a complete spec in one pass. In future spec tasks I will compile all business rules into a checklist before prompting.

---

## Entry 4 — 2026-05-13

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> I did not see how we approached this challenge in the spec doc: For this project, the operations manager considers an elevator overdue if more than 12 months have passed since its last periodic inspection.

**What Happened:**
Claude updated the Overdue Inspections card definition in `docs/dashboard_spec.md`. The original definition used license expiry date as the overdue criterion, which did not reflect the actual business rule. The updated definition specifies: find the most recent record per elevator in `inspection.csv` where `InspectionType` equals `"ED-Periodic Inspection"`; if that record's `Latest_INSPECTION_Date` is more than 12 months before today, the elevator is overdue. Elevators with no periodic inspection on file are also counted as overdue.

**What I Would Change:**
This entry exists entirely because of an omission in Entry 3. The business rule defining "overdue" was stated clearly in the requirements but was not included in the original spec prompt. I would not change how this correction was handled — Claude updated the spec accurately — but I would eliminate the need for this entry entirely by being more thorough when reading requirements before writing a spec. This is a good example of how a vague prompt creates rework.

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
AI generated exactly what was requested in the prompt.  Typically search bars have the magnifying glass as an icon and that was not added with the initial prompt, so I added it with a second prompt.  Other than that everything worked perfectly.

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
The card count mismatch in Task 2 of this entry was a preventable bug. The initial prompt did not specify that card counts should be calculated dynamically from the data — it only described the visual behavior. As a result, Claude hardcoded the counts, which immediately became inconsistent with the filter output. In future prompts involving counts or metrics I will explicitly state "compute dynamically from the data" to prevent static values from being used. I would also have included the spec update request (Task 3) in the original prompt rather than as a follow-up.

---

## Entry 8 — 2026-05-14

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> I want to update the summary cards to Total Elevators, Operational Elevators, Non-Operational Elevators, Overdue Inspections. Would this conflict with Task 5?

**What Happened:**
Claude explained that the dashboard update and Task 5 operate in completely separate parts of the project — the dashboard lives in `platform/` while Task 5 is a Jupyter notebook in `intelligence/`. No conflict exists. Claude noted that Task 5's classification task will define which license statuses are operational vs. non-operational, which could inform the dashboard cards. Two options were presented: update the dashboard now using best-judgment classifications, or complete Task 5 first to establish data-driven definitions before building the new cards. The user decided to finish dashboard tasks first and drill down on functionality afterward.

**What I Would Change:**
I would have mapped out the dependencies between tasks before starting any implementation work. Task 5's classification output directly informs what the dashboard cards should be named and how they should filter — had I completed Task 5 first, the dashboard card definitions would have been data-driven rather than assumption-based. In future projects I will identify which tasks produce outputs that other tasks depend on, and sequence them accordingly.

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
This entry involved four separate prompts that could have been consolidated into two. The card restructuring (Tasks 1 and 2), the sort dropdown (Task 3), and the license expiry highlighting (Task 4) are all independent features. I could have included the sort dropdown and expiry highlighting requirements in the initial card restructuring prompt, reducing the number of back-and-forth exchanges. Going forward I will group related visual and behavioral changes into a single well-structured prompt rather than making incremental requests.

---

## Entry 10 — 2026-05-14

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> Update the docs/dashboard_spec.md file with the following: There will be 5 Summary Cards — Total Elevators, Active Elevators, Inactive Elevators, Overdue Inspections, Expired Licence. Each card will contain additional data showing how many elevators are operational and non-operational.

**What Happened:**
Claude updated `docs/dashboard_spec.md` to reflect the renamed cards (Active Elevators replacing Operational Elevators, Inactive Elevators replacing Non-Operational Elevators) and added a Sub-data section specifying that each card displays a secondary line in the format "X Operational · Y Non-Operational" for that card's filtered subset. The grid layout diagram and all five individual card descriptions were updated accordingly.

**Task 2**

**Prompt:**
> Update the platform/index.html file with the new features for the summary cards. Reference docs/dashboard_spec.md for instructions.

**What Happened:**
Claude regenerated the summary cards in `platform/index.html` from the updated spec. Cards were renamed (Active Elevators, Inactive Elevators), all IDs and filter keys updated accordingly, and a `subData()` helper function was added to compute the operational breakdown for any subset of elevators. Each card received a sub-data `<p>` element displaying "X Operational · Y Non-Operational" in `text-xs` — white when the card is selected, muted gray when unselected. The `selectCard` function was updated to toggle sub-data text color alongside the other card elements.

**Task 3**

**Prompt:**
> The sub data should reflect operational and non-operational.

**What Happened:**
Claude updated the `subData()` function in `platform/index.html` to use the labels "Operational" and "Non-Operational" instead of "Active" and "Inactive". The `docs/dashboard_spec.md` sub-data format, definition lines, and all five card descriptions were updated to match.

**What I Would Change:**
The label correction in Task 3 was avoidable. The spec already used "Operational" and "Non-Operational" terminology — the prompt for Task 2 should have referenced those exact terms rather than allowing Claude to default to "Active" and "Inactive". I would have been more precise in the original implementation prompt, explicitly stating the sub-data labels rather than leaving that detail open to interpretation. This entry is a good example of how ambiguity in a prompt produces output that requires correction.

---

## Entry 11 — 2026-05-14

**Tool:** Claude (claude-sonnet-4-6)

**Task 1**

**Prompt:**
> Update the docs/dashboard_spec.md with the following: add sorting buttons in the header of the Elevator Details table to sort latest, oldest, A-Z, and Z-A. Add these buttons to the left of the sort dropdown.

**What Happened:**
Claude updated `docs/dashboard_spec.md` to document four sort direction buttons (Latest, Oldest, A→Z, Z→A) in the table header bar, positioned between the "Elevator Details" label and the sort dropdown. `platform/index.html` was then updated to implement the buttons with active-state highlighting and combined sort logic integrating with the dropdown, card filter, and search.

**Task 2**

**Prompt:**
> The Latest and Oldest buttons seem to target only inspection dates which can be misleading. Let's drop Newest and Oldest. Update the spec first.

**What Happened:**
Claude explained that Latest/Oldest were tied to `lastInspection` regardless of dropdown context, making them confusing. The spec was updated to remove them, leaving only A→Z and Z→A. The HTML was then updated to match — removing the two buttons and simplifying the sort logic to a single direction-aware function.

**Task 3**

**Prompt:**
> Would it make more sense to just have an up arrow and down arrow? Yes — update the spec first then the HTML.

**What Happened:**
Claude updated `docs/dashboard_spec.md` to replace A→Z and Z→A labels with ↑ and ↓ arrows, noting they are direction-agnostic and work equally well for text, numbers, and dates. `platform/index.html` was updated to display ↑ and ↓ as the button labels.

**What I Would Change:**
This entry went through three iterations — four buttons reduced to two, then relabeled — because the initial prompt did not think through how sort direction buttons would behave across different data types. Latest/Oldest only made sense for dates, not for text columns, which made them misleading. I would have considered the full range of column types before specifying button labels. A better initial prompt would have described the intended behavior (sort the selected column in ascending or descending order) rather than prescribing specific labels, allowing Claude to suggest the most appropriate UI.

---

## Entry 12 — 2026-05-15

**Tool:** Claude (claude-sonnet-4-6)

**Task 5 — Prompting Lab**

**Prompt:**
> Explain the three prompting techniques — zero-shot, few-shot, and chain-of-thought — and walk me through how to apply each one to the three data analysis tasks using the Ontario elevator license dataset.

**What Happened:**
Claude explained each technique in depth before writing anything into the notebook. Zero-shot was described as asking the question directly with no examples or reasoning instructions. Few-shot was described as embedding 2–3 examples of the desired output format inside the prompt before asking the question. Chain-of-thought was described as instructing the model to reason step by step before giving a final answer. Claude then walked through all three tasks (classification of LICENSE STATUS values, calculation of expired license percentage, and geographic distribution analysis) applying each technique individually. For each task, Claude explained what data to provide in the prompt and why, then wrote the prompt-output pairs into `intelligence/prompting_lab.ipynb`. After all nine pairs were completed, a comparison section was written identifying chain-of-thought as the strongest technique across all three tasks and few-shot as the technique that added the least value — with specific evidence from the outputs cited for each conclusion.

**What I Would Change:**
I would have started with a clearer understanding of what data to include in each prompt before beginning. Early in the task I was unsure whether to reference the CSV file by name or paste the actual values — understanding that Claude cannot read files directly and that the data must be provided in the prompt itself would have saved time. In future tasks I would inspect the dataset first, extract the relevant values, and have them ready before writing any prompts.

---

## Entry 13 — 2026-05-15

**Tool:** Claude (claude-sonnet-4-6)

**Task 6 — License Dataset Analysis**

**Prompt:**
> Walk me through each question in Task 6 and write the solutions into intelligence/license_analysis.ipynb with working code and justifications.

**What Happened:**
Claude walked through all five questions before writing any code, explaining the purpose and procedure for each. For question (a), Claude loaded `data/license.csv` into a pandas DataFrame and tested both `ElevatingDevicesNumber` and `ElevatingDevicesLicenseNumber` for uniqueness using `nunique()`, confirming that `ElevatingDevicesNumber` was the correct primary key. For question (b), Claude used `str.split().str[-1]` and `str.split().str[-2]` to extract the country and province from the location string, confirming the majority of elevators are in Ontario, Canada. For question (c), Claude used `value_counts()` to examine all 11 LICENSE STATUS values and filtered the DataFrame to keep only ACTIVE (42,665 rows) and PENDING_RENEWAL (632 rows), justifying each kept and removed status by name with a specific reason. For question (d), Claude re-verified that `ElevatingDevicesNumber` remained unique after filtering and explained the scenario under which filtering could have broken uniqueness. For question (e), Claude parsed `LICENSEEXPIRYDATE` using `pd.to_datetime()`, grouped by year using `dt.year`, and produced a labeled bar chart with a data-derived time axis. The notebook was then executed from the terminal using `jupyter nbconvert` and ran without errors.

**What I Would Change:**
I initially did not understand that pandas was required and needed an explanation of what it is before proceeding. In future data analysis tasks I would familiarize myself with the required libraries beforehand so that setup time is reduced. I would also run the notebook sooner in the process rather than waiting until all five questions were complete — running after each section would catch errors earlier and confirm outputs before moving on.

---

## Summary

This log covers 13 interactions with Claude (claude-sonnet-4-6) across Tasks 1, 5, and 6 of the RocketDash project. The interactions ranged from generating project documentation and building a static HTML dashboard to applying prompting techniques in a Jupyter notebook and performing data analysis on the Ontario elevator registry. Reviewing the entries as a whole reveals five consistent patterns — both in how AI tools were used effectively and where the approach fell short.

---

### Pattern 1 — Incomplete prompts caused the most rework

The single most common source of extra work across this log was prompts that omitted key requirements. Entry 3 produced a dashboard spec missing the 12-month overdue inspection rule, requiring a full correction in Entry 4. Entry 7 produced hardcoded card counts because dynamic behavior was never specified. Entry 10 used incorrect labels because the exact terminology from the spec was not referenced in the prompt. In every case the AI did exactly what was asked — the problem was not the output but the input. Vague or incomplete prompts consistently produced outputs that required correction, which cost more time than writing a complete prompt would have.

**Lesson:** Before submitting a prompt, treat it like a requirements document. Ask: what should the output look like? What business rules apply? What terminology should be used? What behavior is expected across all edge cases? The more specific the prompt, the fewer corrections are needed.

---

### Pattern 2 — Task dependencies were not planned upfront

Entry 8 documents a moment where a dashboard update was almost made before completing Task 5, which would have produced card definitions based on assumptions rather than data. The operational vs. non-operational classification that Task 5 was designed to establish is exactly what the dashboard cards needed. Had the tasks been sequenced correctly — Task 5 first, then dashboard refinement — the card definitions would have been data-driven from the start. The same issue appears in Entry 3, where the dashboard spec was written before all business rules had been extracted from the requirements document.

**Lesson:** Before beginning any task, identify which other tasks it depends on and which tasks depend on it. Build the dependency chain before touching the code or the prompts.

---

### Pattern 3 — Iterative refinement is a feature, not a failure

Several entries show features being built in multiple passes — the sort buttons went through three iterations in Entry 11, the summary cards were updated across four separate entries, and the sub-data labels required correction after implementation. While some of these iterations were caused by incomplete prompts, others were the result of genuinely discovering better solutions through use. The ↑ and ↓ arrows were an improvement over A→Z and Z→A that only became obvious after seeing the buttons in context. This is normal when building with AI tools. The first version of something is rarely the final version. What matters is that each iteration is logged, reviewed, and reflected on.

**Lesson:** Expect iteration. The goal is not to get it right in one prompt but to move toward the right solution efficiently. Logging each change makes the reasoning traceable and helps distinguish planning failures from genuine refinement.

---

### Pattern 4 — Asking for explanation before implementation improved understanding

A consistent practice across Tasks 5 and 6 was asking Claude to explain concepts and procedures before writing any code or notebook content. This was applied to prompting techniques (Entry 12), pandas as a library (Entry 13), and each of the five license analysis questions individually. In every case, understanding the purpose and procedure first produced better prompts and more informed review of the outputs. This contrasts with earlier entries where prompts were submitted without fully understanding what the output would involve, leading to corrections and rework. The shift toward explanation-first interactions represents the most meaningful improvement in how the AI tool was used across the project.

**Lesson:** When working in unfamiliar territory, ask for an explanation before asking for implementation. A two-step approach — understand, then build — consistently produced better results than jumping straight to output generation.

---

### Pattern 5 — The AI performed best when given a reference document

The highest-quality outputs in this log came from prompts that referenced an existing specification. When `docs/dashboard_spec.md` was complete and cited as the source of truth, Claude produced accurate implementations with minimal correction. When the spec was incomplete or not referenced, outputs required rework. This points to a broader principle: AI tools are most effective when the context they are given is structured, complete, and accurate. Building a thorough spec document before implementation is not overhead — it is the most important input to any implementation prompt, and the single factor that most consistently determined whether a prompt succeeded or required correction.

---

## Entry 14 — AND-102, Task 3: Dynamic Dashboard with HTMX

**Tool:** Claude (claude-sonnet-4-6)

**Prompt:**
> Read `docs/dashboard_spec.md` in full. Update it to reflect the interactive behavior introduced in Task 3 (AND-102). Make two additions:
>
> 1. Add a "Server Architecture" section (place it after the Design Philosophy section): The dashboard is no longer a static file. It is served by a Python Flask server at `platform/server.py`. The server loads `platform/elevator_fleet.csv` on startup and serves the dashboard at `/`. All table interactivity is handled by HTMX — the server returns HTML fragments, not JSON. There is no custom JavaScript for filtering or sorting.
>
> 2. Add a "Filters and Sorting" section (place it after the Detail Table section): Status Filter using `hx-get="/elevators?status=<value>"`. City Filter using `hx-get="/elevators?city=<value>"`. Sortable columns (Elevator ID and License Expiry Date) with ascending/descending toggle via query string parameters. The "Showing X of Y elevators" count updates with every fragment response. Keep all existing sections intact. Match the spec's existing formatting and tone.

**Prompting Technique:** Zero-shot

**Why Zero-Shot:** The task was specific and bounded — two clearly described sections with explicit content provided in the prompt. The existing spec file gave Claude the formatting context it needed by reading it. No examples were needed (few-shot) because the format was already present in the file, and no step-by-step reasoning was required (chain-of-thought) because the content of each section was fully specified upfront.

**What Happened:**
Claude read `docs/dashboard_spec.md` in full and added both sections as specified. The "Server Architecture" section was inserted after the Design Philosophy section and describes the Flask server at `platform/server.py`, the CSV loaded on startup, and the HTMX fragment pattern with no custom JavaScript. The "Filters and Sorting" section was inserted after the Detail Table section and documents the Status Filter, City Filter, sortable column behavior, combined query parameter handling, and the live "Showing X of Y" count update. All existing sections were preserved and the new content matched the spec's formatting and tone.

**What I Would Change:**
The prompt produced the correct output without correction. The zero-shot technique was the right choice — the prompt was detailed enough to fully specify the output without needing examples or reasoning steps. In future spec update prompts I would continue this pattern: read the file first, state exactly where each section goes, and describe the content precisely enough that no interpretation is required.

---

## Entry 15 — AND-102, Task 3: Data Preparation Script

**Tool:** Claude (claude-sonnet-4-6)

**Prompt:**
> Write a Python script at `platform/prepare_data.py` that reads `data/license.csv` and produces a cleaned output file at `platform/elevator_fleet.csv`.
>
> Apply the same filtering from Task 6c: keep only rows where `LICENSESTATUS` is `ACTIVE` or `PENDING_RENEWAL`. All other status values should be excluded.
>
> The output CSV must include only these four columns, renamed as shown: `ElevatingDevicesNumber` → `elevator_id`, `LocationoftheElevatingDevice` → `location`, `LICENSESTATUS` → `license_status`, `LICENSEEXPIRYDATE` → `license_expiry`.
>
> Parse `LICENSEEXPIRYDATE` using pandas and write `license_expiry` in `YYYY-MM-DD` format. The script must be runnable from the command line with `python platform/prepare_data.py`. Print a confirmation line on completion showing the row count written.

**Prompting Technique:** Zero-shot

**Why Zero-Shot:** The task was fully specified — exact file paths, known filtering logic from Task 6c, an explicit column mapping table, a defined date output format, and a required confirmation message. The data was already well understood from Module 1 Task 6 analysis. No examples or step-by-step reasoning were needed; a direct instruction was sufficient.

**What Happened:**
Claude checked the `platform/` directory and confirmed `data/license.csv` column names before writing the script. `platform/prepare_data.py` was created using pandas: reads `data/license.csv`, filters to `ACTIVE` and `PENDING_RENEWAL` rows, parses `LICENSEEXPIRYDATE` from `DD-MMM-YY` format using `pd.to_datetime()` with `format="%d-%b-%y"`, renames the four columns, and writes `platform/elevator_fleet.csv`. The script uses `pathlib.Path(__file__)` so it resolves the correct file paths regardless of where it is called from. Running `python3 platform/prepare_data.py` completed without errors and printed `Written 43297 rows to platform/elevator_fleet.csv`. The output CSV was verified to have the correct four-column structure with dates in `YYYY-MM-DD` format.

**What I Would Change:**
The prompt produced the correct output without correction. One improvement would be to specify the source date format (`DD-MMM-YY`) explicitly in the prompt — Claude inferred it correctly from inspecting the file, but stating it upfront would make the prompt self-contained and reduce the chance of a parsing error on a different dataset.

---

## Entry 16 — AND-102, Task 3: Flask Server (Part B)

**Tool:** Claude (claude-sonnet-4-6)

**Prompt:**
> Create a Python Flask server at `platform/server.py`. Load `platform/elevator_fleet.csv` into a pandas DataFrame on startup and extract a `city` column from the location string using `split()[-5]`. Move `platform/index.html` to `platform/templates/index.html`. Serve the dashboard at `GET /`. Expose `GET /elevators` accepting `status`, `city`, `sort`, and `order` query parameters — apply all active filters and sort together, return a `<tbody>` HTML fragment with one `<tr>` per matching elevator, and include `X-Total-Count` and `X-Filtered-Count` response headers. Match the existing badge and date-highlight styling from the current HTML. Update `CLAUDE.md` to reflect the server-driven architecture, Flask and HTMX in the tech stack, the updated `platform/` directory description, and a conventions entry for the Flask server and HTMX fragment pattern.

**Prompting Technique:** Zero-shot

**Why Zero-Shot:** All components were fully specified — file paths, DataFrame setup, city extraction method, route signatures, query parameter names, response format, header names, and every CLAUDE.md change required. No examples or reasoning steps were needed; the instructions were complete enough to produce the correct output directly.

**What Happened:**
Claude read `platform/index.html` in full to match the existing table row structure and badge styling before writing any code. `platform/server.py` was created with Flask: loads `platform/elevator_fleet.csv` on startup, parses `license_expiry` as datetime, extracts `city` using `split()[-5].title()`, and defines `CITIES` and `STATUSES` lists for dropdown population in Part C. The `GET /` route renders `templates/index.html` passing `cities` and `statuses`. The `GET /elevators` route applies status, city, and sort filters, builds an HTML `<tbody>` fragment with matching row styling (green badge for ACTIVE, yellow for PENDING_RENEWAL, red date text for expired licences), appends an `hx-swap-oob` results count span, and returns `X-Total-Count` and `X-Filtered-Count` headers. Flask was not installed on the system; it was installed with `--break-system-packages` before the server could run. The server was verified: `/elevators?status=ACTIVE&sort=elevator_id&order=asc` returned a correctly formatted HTML fragment, and `/elevators?city=Toronto` returned headers showing 43,297 total and 12,185 filtered rows. `platform/index.html` was moved to `platform/templates/index.html`. `CLAUDE.md` was updated with the server-driven description, Flask and HTMX in the tech stack, updated `platform/` directory entry, and two new convention lines.

**What I Would Change:**
The Flask installation was not anticipated in the prompt — specifying "ensure Flask is installed before running" or checking for it upfront would have avoided the install step interrupting the verification. I would also have explicitly stated that `license_status` in the real CSV uses uppercase values (ACTIVE, PENDING_RENEWAL) rather than the mixed-case values in the placeholder data, so badge color definitions would have been correct on the first pass without needing to infer from the data.

---

## Entry 17 — AND-102, Task 3: HTMX Interactivity (Part C)

**Tool:** Claude (claude-sonnet-4-6)

**Prompt:**
> Update `platform/templates/index.html` and `platform/server.py` to add full HTMX interactivity. Think through how filter state, sort state, and HTMX requests interact before writing any code, then implement. Add HTMX CDN. Replace the sort controls with a `<form id="filters">` containing Status and City dropdowns and two hidden sort-state inputs. Convert the Elevator ID and License Expiry column headers into HTMX-triggering buttons using `hx-vals='{"clicked_sort": "..."}` and `hx-include="#filters"`. Add `hx-trigger="load"` to the table for initial population. Update `/elevators` in `server.py` to resolve sort toggle logic using `clicked_sort` vs. the current `sort` hidden input — flip order if same column, reset to `asc` if different. Append five `hx-swap-oob` elements to every response: results count, `sort-field` input, `sort-order` input, and both sort header buttons with updated icons. Remove the hardcoded `elevators` array and all JS filter/render functions; keep the summary card visual state JS.

**Prompting Technique:** Chain-of-thought

**Why Chain-of-thought:** Part C involved three interlocking systems — the filter form state, the sort toggle state, and the server's oob responses — that all had to be consistent. A direct instruction risked producing HTMX attributes that conflicted with the form field names or sort toggle logic that didn't match what the hidden inputs sent. Asking Claude to reason through the interaction before writing code ensured the `clicked_sort` / `sort` / `order` parameter flow was coherent end-to-end before any code was written.

**What Happened:**
Claude reasoned through the full state flow before implementing: a filter dropdown change fires the form's `hx-get` including all hidden fields; a column header click sends `clicked_sort` via `hx-vals` plus all form fields via `hx-include`; the server compares `clicked_sort` to the current `sort` hidden value to determine whether to flip or reset the order. Both files were then updated. `platform/templates/index.html` received the HTMX CDN script, the filter form with Status and City dropdowns populated from Jinja `statuses` and `cities` variables, two hidden inputs for sort state, sortable column header buttons with `↕` indicators, `hx-trigger="load"` on the table element, and the simplified card-only JavaScript. The hardcoded placeholder array and all JS filter/render functions were removed. Card counts were replaced with Jinja template variables (`{{ total }}`, `{{ active }}`, `{{ inactive }}`, `{{ expired }}`). `platform/server.py` was updated with `clicked_sort` toggle logic, search (`q`) support wired to the search input, and five oob elements in every `/elevators` response. Verified: the `GET /` route served the template with HTMX loaded; `/elevators` returned 43,297 rows on load; `status=PENDING_RENEWAL` filtered to 632; `city=Toronto` filtered to 12,185; each response contained 5 `hx-swap-oob` elements.

**What I Would Change:**
The sort icon update via oob-swapped buttons was the most complex part and required careful reasoning about the state flow. I would document this pattern — `clicked_sort` as a separate param distinct from the hidden `sort` field — in `CLAUDE.md` so it doesn't need to be re-derived in future sessions. I would also have wired the search input to HTMX from the start of the prompt rather than relying on Claude to infer it as a natural extension.

---

# AND-102 Business Document