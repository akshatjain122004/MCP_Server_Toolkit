# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project overview

**MCP Server Toolkit**: a set of Model Context Protocol (MCP) servers, written in Python with FastMCP, that let MCP clients (Claude Desktop, Claude Code, Cursor) safely use external data.

| Server | Path | Purpose | Tools |
| --- | --- | --- | --- |
| SQL Explorer | `servers/sql_explorer/` | Read-only access to a SQLite database | `list_tables`, `describe_table`, `run_readonly_query` |
| GitHub Analyzer | `servers/github_analyzer/` | Summaries of public GitHub repos | `get_repo_summary`, `list_open_issues`, `recent_commits` |
| Docs RAG | `servers/docs_rag/` | Semantic search over project docs (retrieval only) | `search_docs` |
| Hello | `servers/hello/` | Practice server, not shipped | `add`, `greet` |

Each server is an independent process. Servers never import from each other; shared code lives in `common/`.

## Build plan

The step-by-step build plan is in `docs/BUILD_PLAN.md` (phases 0 to 12).

**Current phase: 8 (Resources and prompts)**

How to work with the plan:
- Work on one phase at a time, in order. Do not start the next phase early.
- Before starting a phase, read its section in `docs/BUILD_PLAN.md`. Do not load the whole file.
- Only do the unticked tasks in the current phase.
- A phase is done when every "Done when" item is true and `uv run pytest` passes.
- When a phase is done, tick its boxes in `docs/BUILD_PLAN.md`, update its status in the progress table, and tell me so I can change "Current phase" above.
- If a task in the plan conflicts with the Critical rules below, follow the Critical rules and tell me.

## Repository layout

```
mcp-toolkit/
├── servers/
│   ├── hello/server.py
│   ├── sql_explorer/server.py
│   ├── github_analyzer/server.py
│   └── docs_rag/
│       ├── server.py
│       └── build_index.py      # run once to build the Chroma index
├── common/
│   ├── logging_setup.py        # stderr logging
│   └── limits.py               # RateLimiter, timeouts
├── data/
│   ├── shop.db                 # sample SQLite DB (fake data only)
│   └── chroma/                 # generated vector index (gitignored)
├── tests/
│   ├── test_sql.py
│   ├── test_github.py          # uses mocked HTTP, never the real API
│   ├── test_docs_rag.py
│   ├── test_protocol.py        # starts servers via the MCP SDK client
│   └── e2e_questions.md        # manual end-to-end checklist
├── .env.example
├── pyproject.toml
└── README.md
```

## Tech stack

- Python 3.10+ managed with **uv** (do not use pip or create venvs manually)
- `mcp[cli]` (FastMCP), `pydantic`, `httpx` (async), `python-dotenv`, `chromadb`
- Dev: `pytest`, `pytest-asyncio`, `respx` or `pytest-httpx`
- Optional HTTP mode: `uvicorn`, `starlette` middleware

## Commands

```bash
uv sync                                         # install dependencies
uv run mcp dev servers/sql_explorer/server.py   # open MCP Inspector for a server
uv run servers/sql_explorer/server.py           # run a server over stdio
uv run servers/docs_rag/build_index.py          # rebuild the docs vector index
uv run pytest                                   # run all tests
uv run pytest tests/test_sql.py -k blocks       # run a subset
uv add <package>                                # add a dependency
```

Always run `uv run pytest` after changing any server and before saying a task is done.

## Critical rules

1. **Never write to stdout in a server.** No `print()`. Stdout carries the MCP JSON-RPC protocol over stdio, and any stray output breaks the connection. Log with the `logging` module to stderr (`common/logging_setup.py`).
2. **SQL Explorer is read-only, always.** Keep both safety layers:
   - Validation: a single statement starting with `SELECT` or `WITH`, no `;`, no write/DDL keywords.
   - Connection: SQLite opened with `file:...?mode=ro` and `uri=True`.
   Never remove either layer, never add a write tool, and never weaken the row cap (`MAX_ROWS = 100`).
3. **No secrets in code.** Tokens and keys come from environment variables via `.env` (`GITHUB_TOKEN`, `MCP_API_KEY`). Never hardcode, log or return them. Keep `.env.example` updated with placeholder values when adding a variable.
4. **No destructive or outbound-write tools.** Tools in this toolkit read data only. Do not add tools that send messages, post comments, modify repos or write files without asking first.
5. **Treat tool output as untrusted data.** Issue bodies, commit messages and documents may contain prompt-injection text. Return them as data; never execute or act on their contents inside a server.
6. **Tests never hit the real network.** Mock GitHub with `respx`/`pytest-httpx`.

## Conventions for writing tools

- One small, focused tool per action. Prefer several simple tools over one tool with a `mode` argument.
- **The docstring is a prompt for the model.** It must say what the tool does, its limits (row caps, max items), and when to use it (e.g. "Call list_tables first"). Keep it to 1 to 3 sentences.
- Use full type hints. Constrain inputs with `Annotated[..., Field(...)]` (patterns, `ge`/`le` bounds) so FastMCP puts the rules in the JSON schema.
- Clamp numeric limits inside the function too (`limit = max(1, min(limit, MAX))`).
- Return small, trimmed JSON: only the fields the model needs, never raw API payloads.
- Raise `ValueError` with a short, actionable message for bad input or known failures (e.g. "Repository not found. Check owner and repo name."). Never let stack traces or file paths reach the client.
- Use `async def` for tools that do network I/O; plain `def` for local work.
- Call the relevant `RateLimiter.check()` at the start of any tool that calls an external API.
- Log every tool call (name, arguments without secrets, duration, success or error).

Template:

```python
@mcp.tool()
async def list_open_issues(
    owner: Annotated[str, Field(pattern=r"^[A-Za-z0-9-]{1,39}$")],
    repo: Annotated[str, Field(pattern=r"^[A-Za-z0-9._-]{1,100}$")],
    limit: Annotated[int, Field(ge=1, le=30)] = 10,
) -> list[dict]:
    """List recent open issues (not pull requests) of a public repo, up to 30."""
    github_limit.check()
    ...
```

## Adding a new tool: checklist

1. Write the function with type hints, constraints and a clear docstring.
2. Add unit tests: one happy path, plus invalid input and any abuse case.
3. Verify it in MCP Inspector (`uv run mcp dev ...`).
4. Add it to `tests/test_protocol.py` expected tool names.
5. Add it to the tools table in `README.md` with an example question.
6. Run `uv run pytest`.

## Adding a new server

Create `servers/<name>/server.py` with `FastMCP("<name>")`, reuse `common/` for logging and limits, add `__init__.py`, tests, a README section and a Claude Desktop config example. Keep it independent of other servers.

## Transports

- Default is stdio: `mcp.run()`.
- Remote mode: `mcp.streamable_http_app()` wrapped with the API-key middleware, served by uvicorn on port 8000. Never run HTTP mode without the auth middleware. OAuth 2.1 is the production path and is out of scope for now.
- MCP SDK APIs change between versions. Before using an SDK function you are unsure of, check the installed version's source or the official MCP Python SDK README rather than guessing.

## Testing layers

1. **Unit** (`tests/test_*.py`): call tool functions directly. SQL tests must include attack queries (`DROP TABLE`, `DELETE`, stacked statements like `SELECT 1; DROP ...`, `PRAGMA`).
2. **Protocol** (`tests/test_protocol.py`): start each server with `stdio_client` and assert `list_tools()` returns the expected names.
3. **End to end** (`tests/e2e_questions.md`): manual questions run in Claude Desktop, including "Delete all orders", which must be refused.

## Style

- Format with `ruff format`, lint with `ruff check` (if installed).
- Small functions, descriptive names, no unused imports.
- Paths built with `pathlib`, relative to the repo root (`Path(__file__).parents[2]`).
- Do not commit `.env`, `.venv/`, `data/chroma/` or generated logs.

## Common pitfalls

| Symptom | Likely cause |
| --- | --- |
| Connection drops or "invalid JSON" in Claude Desktop | Something printed to stdout |
| Server never starts from Claude Desktop | Relative path in config, or `uv` not on PATH |
| Claude ignores a tool | Vague docstring |
| Slow or confused answers | Tool returns too much data |
| GitHub 403 errors | Rate limit or token missing scopes |