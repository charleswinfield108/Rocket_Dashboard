"""
Smoke test: start the MCP server over stdio and call ping().

Requires the mcp package and its dev extras:
    pip install -e ".[dev]"
Run from platform/mcp/:
    pytest tests/test_smoke.py -v
"""

import json
import pathlib
import pytest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = str((pathlib.Path(__file__).parent.parent / "server.py").resolve())
CWD    = str((pathlib.Path(__file__).parent.parent).resolve())


# ── Unit test (no subprocess) ────────────────────────────────────────────────

def test_ping_unit():
    """ping() returns the expected dict without touching the transport layer."""
    from tools.ping import ping
    assert ping() == {"status": "ok"}


# ── Integration test (full stdio round-trip) ─────────────────────────────────

@pytest.mark.asyncio
async def test_ping_over_stdio():
    """Start the server as a subprocess and call ping via the MCP stdio client."""
    params = StdioServerParameters(
        command="python3",
        args=[SERVER],
        cwd=CWD,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("ping", {})
            assert result.content, "Expected at least one content block"
            data = json.loads(result.content[0].text)
            assert data == {"status": "ok"}
