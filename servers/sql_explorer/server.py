"""Phase 5: SQL explorer server — query the sample shop.db over MCP."""

import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

# Running this file directly (as Claude Desktop does) only puts this file's own
# directory on sys.path, so the project-root `common` package needs a hand.
_PROJECT_ROOT = str(Path(__file__).parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from common.logging_setup import get_logger  # noqa: E402

mcp = MCPServer("sql-explorer")
logger = get_logger("sql-explorer")

DB_PATH = Path(__file__).parents[2] / "data" / "shop.db"
MAX_ROWS = 100
QUERY_TIMEOUT_SECONDS = 5

# Case-insensitive, word-boundary match for any write/DDL keyword.
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b",
    re.IGNORECASE,
)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _validate_select(sql: str) -> str:
    """Layer 1: reject anything that isn't a single read-only SELECT/WITH statement."""
    cleaned = sql.strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise ValueError("Only SELECT or WITH queries are allowed.")
    if ";" in cleaned:
        raise ValueError("Only a single statement is allowed (no ';' inside the query).")
    if _FORBIDDEN_KEYWORDS.search(cleaned):
        raise ValueError("Query contains a forbidden write/DDL keyword.")
    return cleaned


@mcp.tool()
def list_tables() -> list[str]:
    """List every table in the shop database. Call this first to discover what data exists."""
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return [row["name"] for row in rows]
    finally:
        conn.close()


@mcp.tool()
def describe_table(table: str) -> list[dict]:
    """List the columns (name and type) of a table. Call list_tables first to get a valid table name."""
    if table not in list_tables():
        raise ValueError(f"Unknown table: {table!r}. Call list_tables first.")
    conn = connect()
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [{"name": row["name"], "type": row["type"]} for row in rows]
    finally:
        conn.close()


@mcp.tool()
def run_readonly_query(
    sql: str,
    limit: Annotated[int, Field(ge=1, le=MAX_ROWS)] = 50,
) -> list[dict]:
    """Run a single read-only SELECT or WITH query against the shop database and return up to 100 rows.

    Call list_tables and describe_table first to know what to query.
    """
    clamped_limit = max(1, min(limit, MAX_ROWS))
    validated_sql = _validate_select(sql)

    conn = connect()
    start = time.monotonic()
    deadline = start + QUERY_TIMEOUT_SECONDS

    def _abort_if_timed_out() -> int:
        return 1 if time.monotonic() > deadline else 0

    conn.set_progress_handler(_abort_if_timed_out, 1000)
    try:
        rows = conn.execute(
            f"SELECT * FROM ({validated_sql}) LIMIT ?", (clamped_limit,)
        ).fetchall()
        result = [dict(row) for row in rows]
        logger.info("run_readonly_query ok rows=%d duration_ms=%d", len(result), (time.monotonic() - start) * 1000)
        return result
    except sqlite3.OperationalError as exc:
        logger.info("run_readonly_query failed duration_ms=%d", (time.monotonic() - start) * 1000)
        raise ValueError(f"Query failed: {exc}") from exc
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run()
