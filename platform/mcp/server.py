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
from tools.elevators import (
    list_tssa_shutdown_elevators,
    get_inspection_history,
    count_incidents,
    get_incidents_for_elevator,
    list_followup_elevators,
)
from tools.additional import (
    list_expiring_licences,
    list_overdue_inspections,
    get_incident_root_cause_summary,
    list_alterations_pending_followup,
)
from tools.predictions import get_risk_explanation

load_dotenv()  # no-op if .env is absent (e.g. on Render)

mcp = FastMCP("rocket-elevators-mcp")
mcp.add_tool(ping)
mcp.add_tool(list_tssa_shutdown_elevators)
mcp.add_tool(get_inspection_history)
mcp.add_tool(count_incidents)
mcp.add_tool(get_incidents_for_elevator)
mcp.add_tool(list_followup_elevators)
mcp.add_tool(list_expiring_licences)
mcp.add_tool(list_overdue_inspections)
mcp.add_tool(get_incident_root_cause_summary)
mcp.add_tool(list_alterations_pending_followup)
mcp.add_tool(get_risk_explanation)


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
