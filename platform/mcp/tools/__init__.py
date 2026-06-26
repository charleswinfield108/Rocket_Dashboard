# Tools package — each module exposes one or more plain Python functions.
# server.py registers them with FastMCP via mcp.add_tool().
# Tools must not import from server.py to stay independently testable.
