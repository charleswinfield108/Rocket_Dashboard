"""
Rocket Elevators MCP server — entrypoint.

Transport: stdio (default). To add HTTP/SSE transport later, pass
transport="sse" and host/port kwargs to mcp.run() without touching
any tool definitions.

Usage:
    python3 server.py                   # stdio (for Claude Code / Go client)
    python3 server.py --transport sse   # HTTP/SSE (future)
"""

import argparse
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from tools.ping import ping

load_dotenv()  # no-op if .env is absent (e.g. on Render)

mcp = FastMCP("rocket-elevators-mcp")
mcp.add_tool(ping)

# ── Register additional tools here as the sprint progresses ──────────────────
# from tools.elevators import get_elevator, list_shutdowns, inspection_history
# mcp.add_tool(get_elevator)
# ...


def main() -> None:
    parser = argparse.ArgumentParser(description="Rocket Elevators MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport to use (default: stdio)",
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
