# AND-106 Sprint Retrospective

**Sprint:** Module 6 — AI Chatbot
**Date:** 2026-06-19
**Team:** Charles Winfield (solo)

---

## What Went Well

- **REMI responded correctly on first live test.** The system prompt boundaries held cleanly across all five stress-test scenarios — including adversarial prompts and out-of-scope questions — without any hallucination or boundary violations.
- **Render deployment came together faster than expected.** The Blueprint YAML approach (render.yaml) meant the Go API, PostgreSQL, and Flask dashboard all spun up from a single file, which was much faster than configuring each service manually.
- **Docker local stack was solid.** Once WSL integration was enabled and the docker group permissions were set, the three-container stack (db + api + implicit Flask) ran cleanly and mirrored the Render environment closely enough that bugs found locally translated directly to fixes on Render.
- **Iterative prompt refinement worked.** Running real stress-test scenarios against the live model revealed two gaps (shutdown re-inspection steps and order priority comparison), and both were fixed in a single follow-up commit. The evaluation doc now has a complete before/after record.

## What Was Difficult

- **Gunicorn worker timeouts blocked the dashboard data from loading.** The root cause was 91 sequential HTTP calls to the Go API during cache warm-up. The fix (a single PostgreSQL LATERAL JOIN query) was the right call, but diagnosing it cost significant time because the timeout error masked the real issue.
- **Docker networking to Ollama (host.docker.internal) was not reliable.** The Go API container could not consistently reach Ollama on the host machine, which caused intermittent "Sorry, I couldn't get a response" errors in the chat widget. Warming Ollama with a direct curl before testing was a workaround, not a real fix.
- **Working alone compressed the feedback loop.** Without a team to catch mistakes in PR review, several issues (wrong render.yaml property, missing DATABASE_URL, .dockerignore blocking prompts/) had to be discovered through failed deployments rather than caught before push.

## What I Would Do Differently

- Set up a health-check endpoint on Ollama and poll it from the Go API before accepting chat requests — this would surface the host.docker.internal connectivity issue immediately rather than returning a silent error to the user.

## Action Item

**For the next module:** Add a `/api/health` response that includes Ollama reachability status so connectivity issues are visible in the dashboard before a user hits the chat widget.

---

# AND-107 Sprint Retrospective

**Sprint:** Module 7 — Chatbot: Data & Knowledge
**Date:** 2026-06-24
**Team:** Charles Winfield (solo)

---

## Sprint 1 Follow-Through

**Original action item:** Add a `/api/health` response that includes Ollama reachability status so connectivity issues are visible in the dashboard before a user hits the chat widget.

**What was done this sprint:** The `/api/health` endpoint in the Go API was extended to include an Ollama connectivity check. Before AND-107 work began, the health endpoint was reviewed and the Ollama reachability probe was added so that the dashboard could surface LLM availability status without requiring a user to send a chat message first.

**What changed:** Chat errors are now diagnosable at the infrastructure level rather than only surfacing as silent failures in the chat widget. This saved debugging time during AND-107 development by making it immediately clear when Ollama was not reachable from the container, rather than discovering it through a failed user-facing response.

---

## What Went Well

- **MCP server integration gave REMI access to real fleet data.** The chatbot moved from generic elevator knowledge to answering specific questions about devices, inspection history, and risk scores — a meaningful capability jump that the operations team will notice immediately.
- **RAG pipeline connected documentation to answers.** Attaching the maintenance manuals and incident reports as a retrieval source meant REMI could reference actual documentation rather than hallucinating procedure details.
- **OpenRouter made model switching easy.** Swapping between models for evaluation required only a config change, not infrastructure work. This made the model comparison section of the deliverables straightforward to complete.
- **Sprint 1 deployment foundation held up.** Render, PostgreSQL, and the Go API relay were all stable coming into this sprint — no time was lost re-fighting infrastructure from AND-106.

## What Was Difficult

- **Working solo means no parallel progress.** MCP server, RAG pipeline, evaluation, and ceremonies all had to be done sequentially. On a team these would overlap; solo, each one blocks the next.
- **Prompt engineering for tool use required more iteration than expected.** Getting REMI to choose the right tool (database lookup vs. RAG retrieval vs. general knowledge) for a given question took several refinement cycles. The model sometimes over-relied on retrieval when a direct answer was available.
- **Free-tier Render spin-down continued to cause intermittent issues.** The Go API sleeping after inactivity meant the first chat request after a quiet period would time out. The fallback logic added in AND-106 helped but didn't fully eliminate the problem.

## What I Would Do Differently

- Add a keep-alive ping to the Render Go API service so it doesn't spin down during low-traffic periods. A simple scheduled request every 10 minutes would eliminate the cold-start failures entirely.

## Action Item

**For the next module:** Implement a keep-alive mechanism (cron job or external ping service) to prevent Render free-tier spin-down from causing the first chat request of each session to fail.
