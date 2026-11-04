"""Phase 5: SQL explorer server — query sample SQLite databases over MCP."""

import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Annotated

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

# Running this file directly (as Claude Desktop does) only puts this file's own
# directory on sys.path, so the project-root `common` package needs a hand.
_PROJECT_ROOT = str(Path(__file__).parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from common.auth import ApiKeyMiddleware, require_api_key  # noqa: E402
from common.cli import http_port  # noqa: E402
from common.limits import RateLimiter  # noqa: E402
from common.logging_setup import audit, get_logger  # noqa: E402

DEFAULT_HTTP_PORT = 8000

mcp = MCPServer("sql-explorer")
logger = get_logger("sql-explorer")

_DATA_DIR = Path(__file__).parents[2] / "data"

# Whitelist of databases the model may query by name. Never accept a raw
# path from the model — only one of these keys.
DATABASES = {
    "shop": _DATA_DIR / "shop.db",
    "inventory": _DATA_DIR / "inventory.db",
    "hr": _DATA_DIR / "hr.db",
}
DEFAULT_DATABASE = "shop"

DatabaseName = Annotated[
    str,
    Field(description="Database to query. Call list_databases first to see valid names."),
]

MAX_ROWS = 100
QUERY_TIMEOUT_SECONDS = 5
MAX_SQL_LENGTH = 2000

sql_limit = RateLimiter(max_calls=60, period=60)

# Case-insensitive, word-boundary match for any write/DDL keyword.
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b",
    re.IGNORECASE,
)


def connect(database: str) -> sqlite3.Connection:
    if database not in DATABASES:
        raise ToolError(
            f"Unknown database: {database!r}. Call list_databases to see valid names."
        )
    db_path = DATABASES[database]
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _validate_select(sql: str) -> str:
    """Layer 1: reject anything that isn't a single read-only SELECT/WITH statement."""
    cleaned = sql.strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise ToolError("Only SELECT or WITH queries are allowed.")
    if ";" in cleaned:
        raise ToolError("Only a single statement is allowed (no ';' inside the query).")
    if _FORBIDDEN_KEYWORDS.search(cleaned):
        raise ToolError("Query contains a forbidden write/DDL keyword.")
    return cleaned


@mcp.tool()
@audit(logger)
def list_databases() -> list[str]:
    """List every database available to query by name. Call this first to pick a database."""
    return list(DATABASES.keys())


@mcp.tool()
@audit(logger)
def list_tables(database: DatabaseName = DEFAULT_DATABASE) -> list[str]:
    """List every table in the given database. Call list_databases first, then this, before querying."""
    conn = connect(database)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return [row["name"] for row in rows]
    finally:
        conn.close()


@mcp.tool()
@audit(logger)
def describe_table(table: str, database: DatabaseName = DEFAULT_DATABASE) -> list[dict]:
    """List the columns (name and type) of a table. Call list_tables first to get a valid table name."""
    if table not in list_tables(database):
        raise ToolError(f"Unknown table: {table!r}. Call list_tables first.")
    conn = connect(database)
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [{"name": row["name"], "type": row["type"]} for row in rows]
    finally:
        conn.close()


@mcp.tool()
@audit(logger)
def run_readonly_query(
    sql: Annotated[str, Field(max_length=MAX_SQL_LENGTH)],
    database: DatabaseName = DEFAULT_DATABASE,
    limit: Annotated[int, Field(ge=1, le=MAX_ROWS)] = 50,
) -> list[dict]:
    """Run a single read-only SELECT or WITH query against the given database and return up to 100 rows.

    Call list_databases, then list_tables and describe_table, before querying.
    """
    sql_limit.check()
    clamped_limit = max(1, min(limit, MAX_ROWS))
    validated_sql = _validate_select(sql)

    conn = connect(database)
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
        raise ToolError(f"Query failed: {exc}") from exc
    finally:
        conn.close()


def _schema_for(database: str) -> str:
    lines = []
    for table in list_tables(database):
        columns = describe_table(table, database)
        column_list = ", ".join(f"{col['name']} {col['type']}" for col in columns)
        lines.append(f"{table}({column_list})")
    return "\n".join(lines)


@mcp.resource("schema://shop")
def schema_shop() -> str:
    """Full schema of the shop database, one table per line: table(col type, col type, ...)."""
    return _schema_for("shop")


@mcp.resource("schema://inventory")
def schema_inventory() -> str:
    """Full schema of the inventory database, one table per line: table(col type, col type, ...)."""
    return _schema_for("inventory")


@mcp.resource("schema://hr")
def schema_hr() -> str:
    """Full schema of the hr database, one table per line: table(col type, col type, ...)."""
    return _schema_for("hr")


@mcp.prompt()
def sales_report(month: Annotated[str, Field(pattern=r"^\d{4}-\d{2}$")]) -> str:
    """Ask for a sales report (revenue, top products, top customers, one insight) for a given month."""
    return (
        f"Using the shop database, give me a sales report for {month}:\n"
        "1. Total revenue for the month.\n"
        "2. Top 5 products by revenue.\n"
        "3. Top 5 customers by total spend.\n"
        "4. One notable insight about the month's sales."
    )


if __name__ == "__main__":
    if "--http" in sys.argv:
        require_api_key()
        app = mcp.streamable_http_app(host="0.0.0.0")
        app.add_middleware(ApiKeyMiddleware)
        uvicorn.run(app, host="0.0.0.0", port=http_port(DEFAULT_HTTP_PORT))
    else:
        mcp.run()
