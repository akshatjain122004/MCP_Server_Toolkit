# Testing

Tests run with `uv run pytest` and are organised in three layers.

## Unit tests

Each server's tool functions are called directly, bypassing the MCP
protocol. SQL Explorer's unit tests include attack queries such as
`DROP TABLE`, stacked statements like `SELECT 1; DROP TABLE customers`, and
`PRAGMA` calls, all of which must be rejected.

## Protocol tests

A test starts each server through the real MCP SDK client over stdio and
calls `list_tools()` and `call_tool()`, proving the server works through the
actual protocol, not just as plain Python functions.

## End-to-end tests

A checklist of real questions, run by hand in Claude Desktop, including
"Delete all orders," which must always be refused regardless of how it is
phrased.

## Network isolation

GitHub Analyzer tests never touch the real network; HTTP calls are mocked
with `respx` so the test suite is fast and deterministic.
