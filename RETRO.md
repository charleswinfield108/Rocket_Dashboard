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
