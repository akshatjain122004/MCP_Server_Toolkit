"""Phase 11: protocol tests — talk to each server the way a real MCP client does.

Unlike the other test files, these start each server as a subprocess over
stdio (StdioServerParameters + stdio_client + ClientSession) instead of
calling the tool functions directly, so they also exercise the MCP
handshake, tool discovery and (de)serialization.
"""

import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).parents[1]


def _server_params(server_rel_path: str) -> StdioServerParameters:
    # stdio_client only forwards a safe env allowlist by default (no
    # GITHUB_TOKEN), so pass it through explicitly. github_analyzer also
    # falls back to its own .env via load_dotenv() when this is unset, which
    # covers local runs; CI has no .env and relies on this forwarding.
    env = {}
    if "GITHUB_TOKEN" in os.environ:
        env["GITHUB_TOKEN"] = os.environ["GITHUB_TOKEN"]
    return StdioServerParameters(
        command=sys.executable,
        args=[str(PROJECT_ROOT / server_rel_path)],
        cwd=str(PROJECT_ROOT),
        env=env or None,
    )


@pytest.mark.asyncio
async def test_sql_explorer_lists_expected_tools():
    async with stdio_client(_server_params("servers/sql_explorer/server.py")) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert names == {"list_databases", "list_tables", "describe_table", "run_readonly_query"}


@pytest.mark.asyncio
async def test_github_analyzer_lists_expected_tools():
    async with stdio_client(_server_params("servers/github_analyzer/server.py")) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert names == {"get_repo_summary", "list_open_issues", "recent_commits"}


@pytest.mark.asyncio
async def test_docs_rag_lists_expected_tools():
    async with stdio_client(_server_params("servers/docs_rag/server.py")) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert names == {"search_docs"}


@pytest.mark.asyncio
async def test_sql_explorer_run_readonly_query_returns_rows():
    async with stdio_client(_server_params("servers/sql_explorer/server.py")) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("run_readonly_query", {"sql": "SELECT 1 AS n"})
            assert result.is_error is not True
            assert result.structured_content == {"result": [{"n": 1}]}


@pytest.mark.asyncio
async def test_sql_explorer_drop_table_is_rejected():
    async with stdio_client(_server_params("servers/sql_explorer/server.py")) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("run_readonly_query", {"sql": "DROP TABLE customers"})
            assert result.is_error is True
