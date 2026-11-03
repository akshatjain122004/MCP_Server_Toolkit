import logging
import time

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from common.limits import RateLimiter
from common.logging_setup import audit
from servers.docs_rag import server as docs_server
from servers.github_analyzer import server as github_server
from servers.sql_explorer import server as sql_server


def test_audit_logs_one_ok_line_for_a_successful_call(caplog):
    logger = logging.getLogger("test-audit-ok")

    @audit(logger)
    def add(a, b):
        return a + b

    with caplog.at_level(logging.INFO, logger="test-audit-ok"):
        result = add(2, 3)

    assert result == 5
    messages = [r.getMessage() for r in caplog.records]
    assert len(messages) == 1
    assert "tool=add" in messages[0]
    assert "status=ok" in messages[0]


def test_audit_logs_error_status_and_still_reraises(caplog):
    logger = logging.getLogger("test-audit-err")

    @audit(logger)
    def boom():
        raise RuntimeError("bang")

    with caplog.at_level(logging.INFO, logger="test-audit-err"):
        with pytest.raises(RuntimeError):
            boom()

    messages = [r.getMessage() for r in caplog.records]
    assert len(messages) == 1
    assert "tool=boom" in messages[0]
    assert "status=error" in messages[0]


@pytest.mark.asyncio
async def test_audit_supports_async_tools(caplog):
    logger = logging.getLogger("test-audit-async")

    @audit(logger)
    async def add(a, b):
        return a + b

    with caplog.at_level(logging.INFO, logger="test-audit-async"):
        result = await add(2, 3)

    assert result == 5
    messages = [r.getMessage() for r in caplog.records]
    assert len(messages) == 1
    assert "status=ok" in messages[0]


def test_audit_never_logs_a_value_passed_as_the_token_kwarg(caplog):
    """Guards the "never log secrets" rule for any kwarg literally named a secret."""
    logger = logging.getLogger("test-audit-secret")

    @audit(logger)
    def call(token):
        return "ok"

    with caplog.at_level(logging.INFO, logger="test-audit-secret"):
        call(token="super-secret-value")

    messages = [r.getMessage() for r in caplog.records]
    assert "super-secret-value" not in messages[0]


# ---- input validation (max_length on free-text SQL / search queries) ----


@pytest.mark.asyncio
async def test_overlong_sql_is_rejected_before_any_db_connection(monkeypatch):
    called = False

    def fail_if_called():
        nonlocal called
        called = True
        raise AssertionError("connect() should not have been called")

    monkeypatch.setattr(sql_server, "connect", fail_if_called)

    long_sql = "SELECT 1 -- " + ("x" * 2000)
    with pytest.raises(ToolError):
        await sql_server.mcp.call_tool("run_readonly_query", {"sql": long_sql})
    assert called is False


@pytest.mark.asyncio
async def test_overlong_docs_query_is_rejected():
    with pytest.raises(ToolError):
        await docs_server.mcp.call_tool("search_docs", {"query": "x" * 501})


# ---- invalid owner/repo and out-of-range limits are rejected before any HTTP call ----


@pytest.mark.asyncio
async def test_invalid_github_owner_is_rejected_before_any_http_call(monkeypatch):
    called = False

    async def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("gh() should not have been called")

    monkeypatch.setattr(github_server, "gh", fail_if_called)

    with pytest.raises(ToolError):
        await github_server.mcp.call_tool(
            "get_repo_summary", {"owner": "bad owner!", "repo": "flask"}
        )
    assert called is False


@pytest.mark.asyncio
async def test_invalid_github_repo_is_rejected_before_any_http_call(monkeypatch):
    called = False

    async def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("gh() should not have been called")

    monkeypatch.setattr(github_server, "gh", fail_if_called)

    with pytest.raises(ToolError):
        await github_server.mcp.call_tool(
            "get_repo_summary", {"owner": "pallets", "repo": "bad repo!"}
        )
    assert called is False


@pytest.mark.asyncio
async def test_out_of_range_github_limit_is_rejected_before_any_http_call(monkeypatch):
    called = False

    async def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("gh() should not have been called")

    monkeypatch.setattr(github_server, "gh", fail_if_called)

    with pytest.raises(ToolError):
        await github_server.mcp.call_tool(
            "list_open_issues", {"owner": "pallets", "repo": "flask", "limit": 999}
        )
    assert called is False


# ---- rate limiting: raises after the limit, recovers after the window ----


@pytest.mark.asyncio
async def test_sql_rate_limit_blocks_then_recovers(monkeypatch):
    monkeypatch.setattr(sql_server, "sql_limit", RateLimiter(max_calls=2, period=0.05))

    await sql_server.mcp.call_tool("run_readonly_query", {"sql": "SELECT 1"})
    await sql_server.mcp.call_tool("run_readonly_query", {"sql": "SELECT 1"})
    with pytest.raises(ToolError):
        await sql_server.mcp.call_tool("run_readonly_query", {"sql": "SELECT 1"})

    time.sleep(0.06)
    await sql_server.mcp.call_tool("run_readonly_query", {"sql": "SELECT 1"})  # recovered


@pytest.mark.asyncio
async def test_github_rate_limit_blocks_then_recovers(monkeypatch):
    async def fake_gh(path, params=None):
        return {
            "full_name": "pallets/flask",
            "description": None,
            "stargazers_count": 0,
            "forks_count": 0,
            "language": None,
            "open_issues_count": 0,
            "updated_at": "2026-01-01T00:00:00Z",
        }

    monkeypatch.setattr(github_server, "gh", fake_gh)
    monkeypatch.setattr(github_server, "github_limit", RateLimiter(max_calls=1, period=0.05))

    await github_server.mcp.call_tool("get_repo_summary", {"owner": "pallets", "repo": "flask"})
    with pytest.raises(ToolError):
        await github_server.mcp.call_tool(
            "get_repo_summary", {"owner": "pallets", "repo": "flask"}
        )

    time.sleep(0.06)
    await github_server.mcp.call_tool("get_repo_summary", {"owner": "pallets", "repo": "flask"})


# ---- error hygiene: an unexpected crash never leaks a path or traceback ----


@pytest.mark.asyncio
async def test_unexpected_crash_leaks_no_path_or_traceback(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError(f"boom at {__file__}")

    monkeypatch.setattr(github_server, "gh", boom)

    with pytest.raises(ToolError) as exc_info:
        await github_server.mcp.call_tool(
            "get_repo_summary", {"owner": "pallets", "repo": "flask"}
        )

    message = str(exc_info.value)
    assert "Traceback" not in message
    assert ".py" not in message
    assert "boom at" not in message


# ---- audit logging is actually wired into the tools, not just the decorator ----


def test_sql_tool_call_emits_one_audit_line(caplog):
    with caplog.at_level(logging.INFO, logger="sql-explorer"):
        sql_server.run_readonly_query("SELECT 1")

    lines = [r.getMessage() for r in caplog.records if "tool=run_readonly_query" in r.getMessage()]
    assert len(lines) == 1
    assert "status=ok" in lines[0]


# ---- secrets check: the GitHub token never reaches a log line ----


@pytest.mark.asyncio
async def test_github_token_never_appears_in_audit_logs(monkeypatch, caplog):
    monkeypatch.setattr(github_server, "GITHUB_TOKEN", "super-secret-token-value")

    async def fake_gh(path, params=None):
        return {
            "full_name": "pallets/flask",
            "description": None,
            "stargazers_count": 0,
            "forks_count": 0,
            "language": None,
            "open_issues_count": 0,
            "updated_at": "2026-01-01T00:00:00Z",
        }

    monkeypatch.setattr(github_server, "gh", fake_gh)

    with caplog.at_level(logging.INFO, logger="github-analyzer"):
        await github_server.mcp.call_tool(
            "get_repo_summary", {"owner": "pallets", "repo": "flask"}
        )

    for record in caplog.records:
        assert "super-secret-token-value" not in record.getMessage()
