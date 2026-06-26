# AND-106 Sprint Ceremonies — Transcript

**Sprint:** Module 6 — AI Chatbot
**Date:** 2026-06-19
**Participant:** Charles Winfield (solo)

---

## Sprint Planning

**Goal:** Build and deploy REMI — a local LLM-powered chat assistant embedded in the Rocket Elevators Operations Dashboard.

**Deliverables committed this sprint:**
- Go `/api/chat` relay endpoint (Ollama integration)
- REMI system prompt (500+ words, domain-grounded)
- Chat widget embedded in `platform/templates/index.html`
- Render deployment (PostgreSQL + Go API + Flask dashboard)
- Model evaluation with gemma2:2b, stress-test scenarios documented
- Claude Design mockups (2 iterations)
- Trello board with sprint tasks
- RETRO.md

**Definition of Done:** Chat widget live on Render, REMI responds in-domain, system prompt stress-tested, all docs committed to GitHub.

**Estimated effort:** Full-day sprint, solo.

---

## Daily Standup 1 — Morning

**Yesterday:** Completed AND-105 (batch explanation generation and evaluation notebook).

**Today:** Setting up Docker local stack, deploying to Render, writing the REMI system prompt.

**Blockers:** None anticipated — Docker WSL integration needs to be verified.

---

## Daily Standup 2 — Midday

**Yesterday / this morning:** Docker stack running, Render Blueprint deployed (Go API + PostgreSQL + Flask dashboard). System prompt written and committed.

**Today:** Building Go `/api/chat` endpoint, wiring up the chat widget in the frontend.

**Blockers:** Gunicorn worker timeouts on Render blocking dashboard data load — investigating root cause.

---

## Daily Standup 3 — Evening

**Yesterday / this afternoon:** Go chat endpoint built, chat widget live and responding. Gunicorn timeout fixed by switching from 91 sequential HTTP calls to a single PostgreSQL LATERAL JOIN query.

**Today:** Model evaluation complete (5 stress-test scenarios), Claude Design mockups committed, Trello board set up, RETRO.md written.

**Blockers:** None — all deliverables committed.

---

## Sprint Retrospective

**What went well:**
- REMI passed all 5 stress-test scenarios on the first evaluation run.
- Render Blueprint made multi-service deployment fast.
- Docker local stack closely mirrored the Render environment.
- Prompt iteration was clean — two targeted commits fixed both identified gaps.

**What was difficult:**
- Gunicorn worker timeouts masked the real issue (91 sequential HTTP calls) and cost significant debugging time.
- Docker networking to Ollama via `host.docker.internal` was intermittently unreliable.
- Working solo meant no PR review — several issues were discovered through failed deployments.

**Action item:** Add Ollama reachability status to `/api/health` so connectivity issues surface before a user hits the chat widget.
