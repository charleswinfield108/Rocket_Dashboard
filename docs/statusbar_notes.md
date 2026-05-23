# Task 4 — Status Bar Notes

## Screenshot

![Claude Code status bar during an active session](../assets/statusbar_screenshot.png)

---

## Status Bar Values Explained

The status bar produced by `scripts/statusline.sh` displays seven values on a single line:

**`model`** — The Claude model currently handling the session, read from `model.id` (e.g., `claude-sonnet-4-6`). This confirms which model tier is being billed and what capability level is active.

**`ctx`** — Context window usage as a percentage, read from `context_window.used_percentage`. When this approaches 100%, the session is near its limit and older context will begin to be compressed or dropped.

**`cost`** — Total session cost in USD, read from `cost.total_cost_usd`. This is a running total accumulated across all turns since the session started, not a per-turn cost.

**`in`** — Total input tokens in the current context window, read from `context_window.total_input_tokens`. Includes the prompt, all conversation history, file contents read, and cached context loaded into the model.

**`out`** — Total output tokens from the most recent response, read from `context_window.total_output_tokens`. Output tokens are priced at 5× the rate of input tokens, so a long code-generation response has an outsized effect on cost.

**`cache_read`** — Input tokens served from the cache this turn, read from `context_window.current_usage.cache_read_input_tokens`. These cost 90% less than standard input tokens.

**`cache_write`** — Input tokens written to the cache for the first time this turn, read from `context_window.current_usage.cache_creation_input_tokens`. These are processed at full price and stored for reuse in future turns.

---

## Cache Tokens: Read vs. Creation

Claude Code uses prompt caching to reduce cost on repeated context. Two fields inside `context_window.current_usage` track how caching behaved in a given turn:

**`cache_creation_input_tokens`** — Tokens that were written into the cache for the first time. These tokens were processed at full input price and stored so they can be reused in future turns. A high value here means the session is building a cache — normal at the start of a conversation or after context changes significantly.

**`cache_read_input_tokens`** — Tokens that were served from the cache rather than reprocessed. These cost 90% less than standard input tokens. A high value here means caching is working: the model is reusing stable context (such as `CLAUDE.md`, unchanged file contents, or system instructions) without reprocessing it from scratch.

**What each tells you about caching health:** If `cache_read_input_tokens` is consistently high relative to `cache_creation_input_tokens`, prompt caching is working well and session costs are being reduced. If `cache_creation_input_tokens` dominates every turn, the cache is expiring frequently (the 5-minute TTL has elapsed between turns) or the context is changing too much between turns to benefit from caching.
