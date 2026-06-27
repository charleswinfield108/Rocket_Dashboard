"""
Pooled PostgreSQL connection for the MCP server.

Usage:
    from db import get_pool

    pool = get_pool()
    with pool.connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM elevators").fetchone()

The pool is initialised lazily on first call and reused across tool invocations.
POSTGRES_DSN must be set in the environment (or via .env) before calling get_pool().
"""

import os
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Return the shared connection pool, creating it on first call."""
    global _pool
    if _pool is None:
        dsn = os.environ["POSTGRES_DSN"]
        _pool = ConnectionPool(dsn, min_size=1, max_size=5, open=True)
    return _pool


def close_pool() -> None:
    """Close the pool. Call on server shutdown or in test teardown."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
