# AND-106 Chatbot: Brief
## Module 6 Overview

This is the first of three team modules. You and your teammates will build an AI-powered chatbot for the Rocket Elevators Operations Dashboard across three one-week sprints. Each sprint advances the same product: a conversational interface that helps the operations team get answers about their elevator fleet without digging through data manually.

This sprint establishes the foundation: deploy the existing dashboard to shared infrastructure the whole team can access, design and build a chat interface, and craft a system prompt that gives the chatbot deep knowledge of elevator operations. By the end of the week, you will have a chatbot that talks competently about elevator operations, stays in scope, and holds a multi-turn conversation, running locally with Ollama.

This module includes learning cards with optional practice exercises. These exercises are recommended but not graded. Only deliverables listed in this document are evaluated.

## What to Expect

This project is intentionally less guided than modules 1–5. You will run into things you don't know how to do, requirements that feel ambiguous, and tools you haven't used before. You might struggle with deployment, get stuck on integration, or find that your team's plan falls apart on Day 3. This is expected.

Previous modules walked you through tasks step by step. This project gives you a goal and leaves the path to you. You will need to research solutions on your own, make decisions without complete information, and adapt when things don't go as planned. Client requirements may shift between sprints. Your team will need to figure out how to coordinate when three people are touching the same codebase.

Autonomy, the capacity to tackle the unknown, and adaptation to change are all evaluated in this project, alongside the technical work. The learning cards will help with concepts and tools, but they won't hand you a recipe for every problem.

Your instructor is available as a guide and acts as the client, but they are not your first line of support. Logistical issues and critical blockers go to the instructor. Everything else (technical problems, team disagreements, unclear requirements, integration headaches) should be resolved at the team level first. Your resourcefulness and organization as a team are part of what is being evaluated.

## Business Context

The operations team has been using the dashboard and risk explanations from your previous work. The M5 evaluation confirmed that a conversational interface would help technicians get quick answers without navigating multiple screens. Leadership has approved the project:

> "We want a chatbot on the dashboard. Something the operations team can ask, 'Which elevators are due for inspection this month?' or 'What's the maintenance history on that unit at 45 King Street?' and get a clear answer. No more digging through tables.
>
> But we're not just building a chatbot. We're testing whether this team can deliver a real product together. I want to see a proper development workflow: shared infrastructure everyone can access, code reviews on every change, a task board I can check to see where things stand.
>
> Start with the basics this week. Get the dashboard deployed so the whole team can see it. Build the chat interface. Make sure the chatbot knows its domain well enough to answer general elevator operations questions without hallucinating. We'll connect it to live data next sprint."

Your team's goals for this sprint:

- Deploy the existing dashboard and Go API so the team has shared infrastructure
- Design the chat interface using Claude Design, then build it
- Craft a system prompt that gives the chatbot expert-level knowledge of elevator operations
- Connect the chat widget to a local Ollama model for multi-turn conversation
- Establish the team workflow: task board, trunk-based development, PR reviews, daily ceremonies

## Required Tools & Accounts

- **Claude Code CLI** (with Claude Pro subscription for Claude Design access)
- **Docker Desktop** (or Docker Engine + Docker Compose on Linux)
- **Go 1.21+**
- **Ollama** installed with a model pulled (e.g., `llama3.1:8b`, `gemma2`, or similar)
- **Git** configured with a GitHub remote
- **A hosting platform account** for deployment (e.g., Render, Railway, Fly.io; free tiers available)
- **A Trello account** (free tier): trello.com
- **A video call platform** for recorded ceremonies (Zoom, Teams, or Google Meet)

## Team Workflow and Requirements

Starting with this module, you will work in a team following a lightweight agile workflow. Each module is one sprint (one week). Your team and role assignments are provided by your instructor before the sprint begins. This is Sprint 1 of the three-sprint arc.

### Roles

Each sprint, the team has three roles. Everyone builds (including PO and SM); the roles add a thin layer of extra responsibility on top of development work. Roles rotate every sprint, so over the three-sprint arc each person will experience at least two different roles.

| Role | Responsibility |
|------|----------------|
| **Product Owner (PO)** | Prepares the task breakdown before sprint planning. Leads sprint planning. Owns the task board. Decides priority when there's a conflict. Accepts or rejects work as "done." |
| **Scrum Master (SM)** | Runs standups and the retrospective. Schedules all ceremony calls and is responsible for recording them and producing transcripts. Flags when someone is stuck or when the team is drifting. Tracks whether the Definition of Done is being followed. |
| **Developer (Dev)** | Builds. Everyone is a developer, including PO and SM. |

### Task Board

Your team will maintain a Trello board to track work and make progress visible. It's the PO's job to keep it current. Share the board link with your instructor, who will be checking it daily. Add the link to your repo's README so the whole team (and your instructor) can find it in one place.

Four columns: **To Do** (planned, not started), **In Progress** (actively being worked on, max 2 per person), **In Review** (code pushed, waiting for a teammate to review), **Done** (passes the Definition of Done).

**Evaluation:**

- Board has tasks covering the sprint's deliverables
- Tasks move through columns as work progresses (not all moved on Day 5)
- Each task is assigned to a team member
- No more than 2 tasks per person in "In Progress" at any time

### Trunk-Based Development

In modules 1–5 you worked alone and committed directly to main. In a team, that breaks things. Trunk-based development will keep everyone integrated continuously: one shared branch (`main`), short-lived feature branches (hours, not days), one task per branch, one branch per PR, no direct commits to main. Keep your merged branches (don't delete them; instructors use them to trace individual contributions).

**Evaluation:**

- No direct commits to main (all changes come through merged PRs)
- Each PR has at least one reviewer
- Branches are short-lived (created and merged within 1–2 days, not left open all week)
- Merged branches are preserved (not deleted)

## Definition of Done

With AI generating code quickly, the risk is shipping things nobody actually understands or tested. A task is "done" when:

- The code works (manually tested, not just "it compiles")
- The code is committed and pushed
- At least one other team member has reviewed it
- The author can explain what the code does

## Ceremonies

Your team will hold short, structured meetings at key points during the sprint. All of them are recorded with video on, and you'll submit both the video and the transcript for each. The Scrum Master is responsible for scheduling these calls, starting the recording, and producing the transcript file afterward.

**File naming:** `<ceremony>-<team-name>-YYYY-MM-DD.mp4` / `.txt`

### Sprint Planning (~45 min, PO leads)

Before the meeting, the PO reads this business document and breaks the deliverables into tasks on the Trello board. Each task should be small enough that one person can finish it in half a day or less. Flag dependencies and suggest a priority order, but don't assign tasks yet (that happens as a team during planning).

During the meeting:

1. **Read this business document together.** Everyone reads silently. Ask questions as you go. If two people interpret a requirement differently, resolve it now.
2. **Review and refine the task breakdown.** The PO walks the team through the draft board. The team challenges, re-sizes, splits, or merges tasks. If a task feels like "build the chatbot," it's too big. What are the pieces?
3. **Identify dependencies and assign.** Map which tasks can start immediately and which need another task to finish first. When two tasks produce pieces that connect, agree on the contract between them before splitting up. Then team members self-select tasks. Aim for maximum parallel work.

After planning, as you work through the sprint:

- Start with tasks that unblock others. If one task is a prerequisite for two other people's work, that task is the team's top priority.
- Merge working code early. Something basic your teammate can build on is better than something polished that lands on the last day.
- Everyone develops locally first. Deployment gives the team a shared URL, but local development with `docker compose up` remains the primary workflow.

**Evaluation:**

- Recording + transcript submitted (PO leads, full team present, cameras on)
- The team discusses task decomposition, dependencies, and assignment (not just the PO dictating)
- Tasks are broken down to half-day-or-less scope

### Daily Standups (×3: Tue, Wed, Thu; ~15 min each, SM leads)

Each person answers: what they shipped yesterday, what they're working on today, and whether they're blocked.

**Evaluation:**

- 3 recordings + transcripts submitted (SM leads, cameras on)
- Each team member reports on progress, current work, and blockers
- Standups stay focused on status (not extended problem-solving; discussions are taken offline)

### Sprint Review + Retrospective (~60 min; PO leads review, SM facilitates retro)

The team demos working software (not slides or descriptions). The PO walks through the task board: what's done, what's not, why. Each developer explains the piece they built. Then the team reflects on what went well, what didn't, and picks ONE concrete change for next sprint.

**Evaluation:**

- Recording + transcript submitted (cameras on)
- Working software is demonstrated
- Each team member explains their contribution
- The retro produces a specific, actionable change for next sprint (not vague intentions like "communicate better")

### RETRO.md

After the retrospective, commit a summary to the repo: 3–5 bullet points covering what went well, what didn't, and one concrete action item for next sprint.

**Evaluation:**

- Covers all three retro questions with specific observations (not generic)
- Committed to the repo root as `RETRO.md`

## Product Requirements

### Deployed Operations Platform

The existing dashboard and Go API are deployed and accessible via a public URL. The operations team can view the dashboard from any browser without running anything locally. Add the public URL to your repo's README.

Render (free tier) is one option that works well for this. Your team is free to use any hosting platform, but the choice is yours to research, evaluate, and agree on. The only requirement is that it works.

**Evaluation:**

- The dashboard loads at a public URL without errors
- All API endpoints respond correctly on the deployed instance (same data as local)
- PostgreSQL is hosted and populated with the Ontario elevator data
- The deployment recovers after inactivity (if using a free tier that sleeps, the app must come back up when accessed)

### Chat Interface

The operations team needs a way to ask questions without leaving the dashboard. A chat interface is embedded directly in the dashboard so users can get answers while still seeing their data. Since Ollama runs as a local service, the chat widget needs a backend to relay messages between the browser and the model; the existing Go API is a natural fit for this. The exact design (layout, positioning, how it opens and closes) is up to your team, planned through Claude Design before implementation.

**Evaluation:**

- The chat interface is accessible from the dashboard without navigating away
- The user can open and close the chat without losing the dashboard context
- The interface supports text input and displays a conversation history (user messages and chatbot responses)
- Multi-turn conversation works (previous messages remain visible and inform the chatbot's responses)
- The interface is usable (text is readable, input is accessible, scrolling works for long conversations)
- The UI design was planned with Claude Design before implementation (see AI-Native Requirements)

### Domain Knowledge

The chatbot answers general elevator operations questions competently. It knows elevator terminology, inspection types, common failure modes, maintenance procedures, and safety concepts. It stays in scope and does not hallucinate facts.

**Evaluation:**

- The chatbot answers general elevator operations questions accurately based on the knowledge in its system prompt
- The chatbot stays in character and within its defined scope (does not answer unrelated questions, does not claim capabilities it does not have)
- Responses are conversational, concise, and professional in tone
- The chatbot acknowledges when it does not know something rather than fabricating an answer
- The chatbot maintains coherence across multiple turns in a conversation

## AI-Native Requirements

### Claude Design for UI Planning

Use Claude Design to plan the chat widget before building it. This is an iterative design process: describe what you want, review the mockup, refine through conversation. The result is a visual plan that guides implementation.

**Evaluation:**

- Claude Design conversation exported and committed to `docs/chat-design/` (screenshots or exported artifacts showing the design iterations)
- The implemented chat widget reflects the final design from Claude Design (layout, positioning, visual style)
- At least 2 design iterations are visible (initial concept and at least one refinement based on feedback)

### System Prompt Engineering

The system prompt is what makes the chatbot a knowledgeable colleague instead of a generic language model. It defines who the chatbot is, what it knows, how it talks, and what it will and won't do. In M106 the chatbot has no database access, so it is only as good as its brief. Everything it knows comes from what you write into the prompt.

Use the Rocket Elevators Operations Handbook and your existing dataset as sources for domain knowledge. The handbook is your client handoff: it describes how the operations team works, what procedures they follow, and what terminology they use. Your job is to read it, decide what the chatbot needs to know, and synthesize it into a well-structured brief.

The system prompt should include:

1. **Agent identity and role:** give it a name, define who it serves and what it does
2. **Domain knowledge:** distilled from the operations handbook. The chatbot should be able to help the operations team with:
   - Explaining what inspection outcomes mean and what happens next
   - Walking through the process after a TSSA shutdown or failed inspection
   - Explaining compliance order urgency and how to prioritize work
   - Clarifying the difference between device statuses, inspection types, and alteration categories
   - Describing incident reporting and root cause categories
   - Answering general elevator operations terminology questions
3. **Tone and communication style:** the chatbot is a knowledgeable colleague, not a search engine
4. **Boundaries:** what it will and will not do, what it knows and does not know. The chatbot cannot look up specific elevators or access the database yet; it must be honest about this limitation
5. **Handling of edge cases:** out-of-scope questions, requests for specific data, questions it cannot answer confidently

The brief will evolve across sprints. In Module 7, the chatbot gains access to real data and detailed reference documents. The brief will shift from being the sole source of knowledge to being the operating manual that governs how the chatbot uses its tools and data.

**Evaluation:**

- System prompt committed to the repo at `platform/api/prompts/system_prompt.md`
- The system prompt is at least 500 words (a thorough brief requires depth; one paragraph is not enough)
- The prompt addresses all five elements listed above

### Model Selection and System Prompt Evaluation

Your chatbot will run on a local Ollama model. Different models handle the same system prompt very differently: some follow boundaries well, others drift off-topic; some give concise answers, others ramble. Picking the right model for your use case is a production skill.

Test your system prompt with at least 2–3 different Ollama models. For each, evaluate how well it follows the brief: does it stay in character? Does it respect boundaries? Are the domain answers accurate and useful? Does it acknowledge what it doesn't know? Consider tradeoffs between response quality, speed, and resource usage. Choose one and justify the decision.

The model you choose here will carry forward into the next sprints for local development.

Then use Claude Code or `claude -p` to stress-test the system prompt itself. A strong model evaluating prompts deployed on a weaker model is a real production technique. Prompt Claude to act as different users (confused technician, adversarial user, operations manager asking edge-case questions) and find gaps, ambiguities, or scenarios the brief does not handle.

**Evaluation:**

An evaluation log committed to `docs/system-prompt-evaluation.md` documenting:

- Which models were tested and how each performed with the system prompt
- The chosen model and the reasoning behind the choice
- At least 5 stress-test scenarios run with Claude (different user types or edge cases)
- The chatbot's response to each scenario
- Gaps or weaknesses identified
- Revisions made to the system prompt based on findings

The system prompt shows evidence of iteration (git history with at least 2 commits modifying the prompt based on evaluation feedback).

**Example evaluation log entry:**

> **Model:** llama3.1:8b
> **Boundary adherence:** Stayed in character for 8/10 test questions. Drifted when asked about general AI topics.
> **Domain accuracy:** Correctly explained periodic vs. follow-up inspections. Confused Minor A and Minor B alteration categories.
> **Response style:** Concise and professional. Occasionally too brief on multi-part questions.
>
> **Stress-test: Operations manager asks about a specific elevator**
> **Prompt:** "What's the inspection history for the elevator at 100 Queen Street?"
> **Response:** [chatbot's actual response]
> **Assessment:** Correctly stated it cannot look up specific devices. Did not suggest an alternative. Added fallback instruction to the system prompt.

### AI-Assisted PR Review

Every pull request requires at least one review before merging. Reviewers may use AI tools as part of their review process, but must add their own assessment beyond what AI surfaces.

**Evaluation:**

- PR history on GitHub shows reviews on merged PRs
- PRs include reviewer comments that go beyond AI-generated findings (the reviewer's own assessment of whether an AI-flagged issue is real, or something they caught that AI did not)

## Improvements and Additional Features

If you make improvements beyond what the requirements specify or add features not listed, document them in `docs/improvements.md` with a description of what you changed, where, and why. Undocumented improvements will not be evaluated.

## Deliverables Summary

| # | Deliverable | Description | Submission Format |
|---|-------------|-------------|-------------------|
| 1 | Deployed application | Dashboard + Go API + PostgreSQL deployed, accessible via public URL | Public URL |
| 2 | Chat interface | Chat widget integrated into the dashboard, connected to Ollama locally | Code in GitHub repo |
| 3 | System prompt | Production-quality brief defining persona, knowledge, boundaries, tone | `platform/api/prompts/system_prompt.md` |
| 4 | System prompt evaluation | Stress-test results and iteration log | `docs/system-prompt-evaluation.md` |
| 5 | Claude Design artifacts | UI planning conversation and iterations | `docs/chat-design/` |
| 6 | Task board | Sprint task tracking | Trello board link |
| 7 | Ceremony recordings + transcripts | Sprint planning, 3 standups, sprint review + retro | 5 recordings + 5 transcripts |
| 8 | RETRO.md | Retrospective summary (3–5 bullets, one action item for next sprint) | Committed to repo |
| 9 | GitHub repository | All code, PRs with reviews, trunk-based git history | Shared repo link |
