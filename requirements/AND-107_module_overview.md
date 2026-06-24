# AND-107 Chatbot: Data & Knowledge

## Business Context

The operations team manages over 40,000 elevators across Ontario. Every day they make decisions about inspections, maintenance, and safety that depend on data spread across databases, PDF manuals, and incident reports. The chatbot from Sprint 1 can discuss elevator operations in general, but it can't answer questions about specific elevators or reference actual documentation.

This sprint, the chatbot becomes the single place the operations team goes for answers. It needs access to the elevator database, the maintenance documentation, and the incident history. It needs to be able to take action, not just answer questions. And it needs to be deployed so the operations team can use it from the dashboard, not just on your laptops.

## Prerequisites

The following must be in place before sprint planning:

- Chat widget integrated into the dashboard, connected to Ollama locally
- System prompt committed at `platform/api/prompts/system_prompt.md`
- Go API with `/api/chat` endpoint handling multi-turn conversation
- Dashboard and Go API deployed on Render (or chosen platform) with PostgreSQL
- PostgreSQL database with five tables: elevators, inspections, incidents, alterations, predictions
- Trunk-based development workflow established (PRs, reviews, Trello board)
- `CLAUDE.md` with project conventions
- `RETRO.md` from Sprint 1 with one concrete action item for this sprint

## New Tools for This Sprint

- Python 3.10+ (for the MCP server and RAG pipeline)
- An OpenRouter account (free tier): openrouter.ai

## Team Workflow

This is Sprint 2. All team workflow requirements from AND-106 carry forward: roles, task board, trunk-based development, Definition of Done, ceremonies, and PR reviews. Refer to the Agile Workflow Guide and the AND-106 business document for the full process. Below are the Sprint 2-specific details.

### Role Rotation

Roles rotate from Sprint 1 (instructor confirms new assignments).

### Retro Follow-Through

The Sprint 1 `RETRO.md` includes a concrete action item for this sprint. Start sprint planning by reviewing that action item as a team:
- Read it aloud
- Agree on how it will be applied this sprint
- Note it on the Trello board

At the end of this sprint, document what was done about it in the Sprint 2 `RETRO.md` section:
- State the original action item
- What changed
- Whether it helped

### Ceremonies

Same structure as Sprint 1 — 5 recordings + 5 transcripts. Sprint planning can be shorter (~30 min) since the process is already familiar.
