"""Health-check tool — verifies the MCP server is reachable."""


def ping() -> dict:
    """Return a status:ok payload. No dependencies, always succeeds."""
    return {"status": "ok"}
