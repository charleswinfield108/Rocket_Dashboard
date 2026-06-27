# Rocket Elevators MCP Server

MCP (Model Context Protocol) server that exposes the Rocket Elevators data layer as tools. Consumed by the Go API chat relay and by Claude Code during development.

## Installation

```bash
cd platform/mcp
pip install -e ".[dev]"   # includes pytest and pytest-asyncio
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_DSN` | Full PostgreSQL connection string | _(required for DB tools)_ |
| `CHROMA_PATH` | Filesystem path for ChromaDB persistence | `./chroma_data` |

The server loads `.env` automatically on startup via `python-dotenv`. On Render, set these as environment variables in the service dashboard instead.

## Running

```bash
# stdio transport (default) — used by Claude Code and the Go API client
python3 server.py

# HTTP/SSE transport (future)
python3 server.py --transport sse
```

## Available Tools

| Tool | Description |
|---|---|
| `ping` | Health check — returns `{"status": "ok"}` |

More tools will be added as each AND-107 task is implemented.

## Adding a New Tool

1. Create `tools/<name>.py` with a plain Python function. The function's docstring becomes the tool description visible to the LLM.
2. Register it in `server.py`:
   ```python
   from tools.<name> import <function>
   mcp.add_tool(<function>)
   ```
3. Add a unit test in `tests/`.

Tools must not import from `server.py`. Keep them independently testable.

## Running Tests

```bash
cd platform/mcp
pytest tests/ -v
```

The smoke test (`test_smoke.py`) runs both a unit test (no subprocess) and a full stdio round-trip test that spawns the server as a subprocess.

## Module Structure

```
platform/mcp/
├── server.py          # Entrypoint — registers tools, runs FastMCP
├── db.py              # Pooled PostgreSQL connection (psycopg3)
├── chroma.py          # ChromaDB client for RAG retrieval
├── tools/
│   ├── __init__.py
│   └── ping.py        # Health-check tool
├── tests/
│   ├── conftest.py    # sys.path setup for pytest
│   └── test_smoke.py  # Unit + stdio integration tests
├── pyproject.toml
├── .env.example
└── README.md
```
