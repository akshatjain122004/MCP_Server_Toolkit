# Build Plan: MCP Server Toolkit

The step-by-step plan for building this project from an empty folder to a published repo.

## How to use this file

- Work on **one phase at a time**, in order. Each phase builds on the one before it.
- Each phase has a **goal**, the **files** it touches, **tasks** with checkboxes, a **done when** check, and the **commands** to verify it.
- A phase is complete only when every "done when" item is true and `uv run pytest` passes.
- Tick the boxes (`- [x]`) as tasks finish, then update `Current phase` in `CLAUDE.md`.
- Rules in `CLAUDE.md` (no stdout, read-only SQL, no secrets in code) apply in every phase.

## Progress overview

| # | Phase | Main output | Est. time | Status |
| --- | --- | --- | --- | --- |
| 0 | Prerequisites | Tools installed, token created | 0.5 day | ✅ |
| 1 | Project structure | Repo skeleton, sample DB | 0.5 day | ✅ |
| 2 | Hello server | First working MCP server | 0.5 day | ✅ |
| 3 | MCP Inspector | Tools verified by hand | 0.25 day | ✅ |
| 4 | Claude Desktop | Tools usable in chat | 0.25 day | ✅ |
| 5 | SQL Explorer | 3 read-only DB tools | 3 days | ✅ |
| 6 | GitHub Analyzer | 3 async API tools | 3 days | ✅ |
| 7 | Docs RAG | Index + `search_docs` | 3 days | ✅ |
| 8 | Resources and prompts | `schema://shop`, 2 prompts | 0.5 day | ✅ |
| 9 | Security hardening | Validation, rate limits, audit log | 1.5 days | ✅ |
| 10 | Remote HTTP + auth | `--http` mode with API key | 1 day | ✅ |
| 11 | Automated testing | Protocol tests, CI | 1.5 days | ⬜ |
| 12 | Packaging and publishing | Docker, README, demo, release | 2 days | ⬜ |

Status key: ⬜ not started · 🟨 in progress · ✅ done

---

## Phase 0: Prerequisites

**Goal:** have every tool installed and a GitHub token ready, so later phases never stop for setup.

**Why:** Claude Desktop starts servers with a single command (`uv run ...`). If `uv` or Python is missing or the wrong version, nothing later works.

### Tasks

- [ ] Install Python 3.10 or newer
- [ ] Install `uv`
  - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] Install Node.js (LTS), needed only for MCP Inspector
- [ ] Install Git and configure name and email
- [ ] Install Claude Desktop and sign in
- [ ] Create a GitHub fine-grained personal access token with **read-only** access to public repositories; store it in a password manager for now
- [ ] Optional: install `ruff` (`uv tool install ruff`)

### Done when

- [ ] `python --version` shows 3.10+
- [ ] `uv --version`, `node --version` and `git --version` all work
- [ ] Claude Desktop opens and you can chat
- [ ] You have a GitHub token saved somewhere safe (not in any file in the repo)

---

## Phase 1: Project structure

**Goal:** a clean repository skeleton with dependencies installed and a realistic sample database.

**Why:** one folder per server keeps each server independent (a crash in one never affects another), and fake but realistic data makes every later test and demo meaningful.

### Files

```
pyproject.toml
.gitignore
.env.example
servers/__init__.py
servers/{hello,sql_explorer,github_analyzer,docs_rag}/__init__.py
common/__init__.py
common/logging_setup.py
scripts/seed_db.py
data/shop.db                (generated)
tests/__init__.py
docs/BUILD_PLAN.md          (this file)
CLAUDE.md
README.md
LICENSE
```

### Tasks

- [ ] `uv init mcp-toolkit` and `cd mcp-toolkit`
- [ ] Add runtime dependencies: `uv add "mcp[cli]" pydantic httpx python-dotenv chromadb`
- [ ] Add dev dependencies: `uv add --dev pytest pytest-asyncio respx faker`
- [ ] Create the folders and empty `__init__.py` files listed above
- [ ] Write `.gitignore` including: `.venv/`, `.env`, `__pycache__/`, `data/chroma/`, `*.log`
- [ ] Write `.env.example`:
  ```text
  GITHUB_TOKEN=your_github_token_here
  MCP_API_KEY=change-me
  ```
- [ ] Write `common/logging_setup.py`:
  ```python
  import logging, sys

  def get_logger(name: str) -> logging.Logger:
      logging.basicConfig(
          stream=sys.stderr,  # never stdout: stdout carries the MCP protocol
          level=logging.INFO,
          format="%(asctime)s %(name)s %(levelname)s %(message)s",
      )
      return logging.getLogger(name)
  ```
- [x] Write `scripts/seed_db.py` that creates `data/shop.db` with:
  - `customers(id, name, email, city, created_at)`, about 60 rows, cities such as Jaipur, Udaipur, Delhi, Mumbai, Bengaluru
  - `products(id, name, category, price)`, about 20 rows
  - `orders(id, customer_id, product_id, quantity, total, order_date)`, about 300 rows spread over the last 6 months
  - Use `Faker` with a fixed seed (`Faker.seed(42)`) so data is the same on every run
  - Delete and recreate the file each run so it is idempotent
- [ ] Add the MIT `LICENSE`
- [ ] `git init`, first commit

### Done when

- [ ] `uv sync` succeeds on a fresh clone
- [x] `uv run scripts/seed_db.py` creates `data/shop.db`
- [x] `sqlite3 data/shop.db "SELECT COUNT(*) FROM orders"` returns about 300
- [ ] `git status` shows no `.env` or `.venv`

---

## Phase 2: Hello server

**Goal:** a minimal working MCP server, to learn the mechanics before writing real logic.

**Why:** with only two trivial tools, any problem is clearly about MCP setup, not your code.

### Files

- `servers/hello/server.py`

### Tasks

- [ ] Create the server:
  ```python
  from mcp.server.fastmcp import FastMCP

  mcp = FastMCP("hello")

  @mcp.tool()
  def add(a: int, b: int) -> int:
      """Add two whole numbers and return the sum."""
      return a + b

  @mcp.tool()
  def greet(name: str) -> str:
      """Return a friendly greeting for the given person's name."""
      return f"Namaste, {name}!"

  if __name__ == "__main__":
      mcp.run()
  ```
- [ ] Understand what each part becomes:
  - function name → tool name
  - type hints → input schema
  - docstring → tool description the model reads
  - `mcp.run()` → listens on stdin/stdout (stdio transport)

### Done when

- [ ] `uv run servers/hello/server.py` starts and waits silently (no output, no crash); stop it with Ctrl+C

---

## Phase 3: Test with MCP Inspector

**Goal:** call every tool by hand and see the raw protocol messages.

**Why:** the Inspector takes the AI out of the picture. If a tool fails here, the bug is in your code, not in Claude or the connection.

### Tasks

- [ ] Run `uv run mcp dev servers/hello/server.py`
- [ ] Click **Connect**, open **Tools**, click **List Tools**
- [ ] Call `add` with `a=4, b=5` and confirm the result is `9`
- [ ] Call `greet` with your name
- [ ] Open the history panel and read the `tools/list` and `tools/call` JSON-RPC messages
- [ ] Deliberately break the code (e.g. a typo), see the error in the Inspector, fix it, click **Restart**

### Done when

- [ ] Both tools are listed with correct descriptions and input fields
- [ ] Both return correct results
- [ ] You can explain what `tools/list` and `tools/call` do

**Rule for all later phases:** never connect a server to Claude Desktop until every tool works in the Inspector.

---

## Phase 4: Connect to Claude Desktop

**Goal:** use your tools from a real chat.

### Tasks

- [ ] Open **Settings → Developer → Edit Config**
- [ ] Add (use your **absolute** path):
  ```json
  {
    "mcpServers": {
      "hello": {
        "command": "uv",
        "args": ["--directory", "/absolute/path/to/mcp-toolkit", "run", "servers/hello/server.py"]
      }
    }
  }
  ```
- [ ] Fully quit Claude Desktop (including the system tray) and reopen it
- [ ] Ask: "What is 128 plus 391? Use your tool." Approve the tool call
- [ ] Find the log folder (**Settings → Developer → Open Logs Folder**) and look at the server log
- [ ] Experiment: add a `print("debug")` to the server, restart, see the connection break, then remove it. This shows why stdout is forbidden.

### Done when

- [ ] `add` and `greet` appear in the tools menu
- [ ] Claude answers 519 using your tool
- [ ] You know where the logs are

### Troubleshooting

| Symptom | Fix |
| --- | --- |
| Tools don't appear | Absolute path? Fully restarted? |
| "spawn uv ENOENT" in logs | Use the full path to `uv` in `command` (`where uv` / `which uv`) |
| Connection closes immediately | Something printed to stdout, or an import error; check logs |

---

## Phase 5: SQL Explorer

**Goal:** let Claude explore and query `shop.db` safely: discover tables, read columns, run read-only queries.

**Why:** this is the core server and the strongest resume point. The LLM writes the SQL; the server guarantees it is safe.

### Files

- `servers/sql_explorer/server.py`
- `tests/test_sql.py`

### Tool design

| Tool | Input | Returns | Purpose |
| --- | --- | --- | --- |
| `list_tables` | none | `list[str]` | Discover what data exists |
| `describe_table` | `table: str` | `list[{name, type}]` | Learn columns before writing SQL |
| `run_readonly_query` | `sql: str`, `limit: int = 50` | `list[dict]` (max 100 rows) | Answer the question |

### Tasks

- [x] Set constants: `DB_PATH = Path(__file__).parents[2] / "data" / "shop.db"`, `MAX_ROWS = 100`
- [x] Write `connect()` opening `f"file:{DB_PATH}?mode=ro"` with `uri=True`, `timeout=5`, and `row_factory = sqlite3.Row`
- [x] Implement `list_tables` (query `sqlite_master` where `type='table'`, exclude `sqlite_%` tables)
- [x] Implement `describe_table`:
  - [x] reject any table name not returned by `list_tables` with a helpful `ValueError`
  - [x] return `PRAGMA table_info` as `{name, type}` pairs
- [x] Implement `run_readonly_query` with **layer 1 validation**:
  - [x] strip whitespace and one trailing `;`
  - [x] must start with `select` or `with` (case-insensitive)
  - [x] reject any remaining `;` (stacked statements)
  - [x] reject keywords with word boundaries: `insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum`
  - [x] clamp `limit` to `1..MAX_ROWS`
  - [x] wrap as `SELECT * FROM (<sql>) LIMIT ?`
- [x] Keep **layer 2**: the read-only connection, even though validation exists
- [x] Add a query timeout with `conn.set_progress_handler` (abort after ~5 seconds)
- [x] Log every query to stderr via `common/logging_setup.py`
- [x] Write clear docstrings (what, limits, when to use), e.g. "Call list_tables first"
- [x] Write `tests/test_sql.py`:
  - [x] `list_tables` returns the three tables
  - [x] `describe_table("customers")` includes `city`
  - [x] `describe_table("users; --")` raises `ValueError`
  - [x] a valid SELECT returns rows
  - [x] a `WITH ... SELECT` query works
  - [x] row cap: `limit=5000` returns at most 100 rows
  - [x] parametrised attacks all raise `ValueError`: `DROP TABLE customers`, `DELETE FROM orders`, `SELECT 1; DROP TABLE customers`, `select * from customers; update orders set total=0`, `PRAGMA table_info(customers)`, `ATTACH DATABASE 'x.db' AS x`
  - [x] column names containing keywords (e.g. `created_at`) still work
- [x] Verify all three tools in the Inspector
- [x] Add `sql-explorer` to the Claude Desktop config

### Done when

- [x] `uv run pytest tests/test_sql.py` passes
- [x] In Claude Desktop, "Which city has the most customers?" is answered correctly via `list_tables` → `describe_table` → `run_readonly_query`
- [x] "Delete all orders" is refused and `orders` still has all rows
- [x] You can explain why there are two safety layers

### Stretch

- [ ] Replace regex validation with `sqlglot` parsing (allow only a single `Select` expression)

---

## Phase 6: GitHub Analyzer

**Goal:** answer questions about public repositories through the GitHub REST API, returning compact results.

**Why:** teaches async tools, secret handling, friendly errors and trimming large API payloads.

### Files

- `servers/github_analyzer/server.py`
- `common/limits.py` (basic version; hardened in Phase 9)
- `tests/test_github.py`
- `.env` (local only)

### Tool design

| Tool | Input | Returns |
| --- | --- | --- |
| `get_repo_summary` | `owner`, `repo` | full_name, description, stars, forks, language, open issues, updated_at |
| `list_open_issues` | `owner`, `repo`, `limit=10` (max 30) | number, title, labels, url; pull requests excluded |
| `recent_commits` | `owner`, `repo`, `limit=10` (max 30) | short sha, first line of message, author, date |

### Tasks

- [x] Put your token in `.env` as `GITHUB_TOKEN=...`; load it with `python-dotenv`
- [x] Fail fast at startup with a clear stderr log if `GITHUB_TOKEN` is missing
- [x] Write an async helper `gh(path, params)` using `httpx.AsyncClient(timeout=10)` with headers `Authorization: Bearer <token>` and `Accept: application/vnd.github+json`
- [x] Map errors to friendly `ValueError`s:
  - [x] 404 → "Repository not found. Check owner and repo name."
  - [x] 403/429 → "GitHub rate limit reached. Try again later."
  - [x] timeout → "GitHub did not respond in time."
- [x] Implement the three tools as `async def`, each returning only the fields in the table above
- [x] Filter out items with a `pull_request` key in `list_open_issues`
- [x] Clamp `limit` to `1..30`
- [x] Write `tests/test_github.py` with `respx` mocks (no real network):
  - [x] summary returns exactly the expected keys
  - [x] issues exclude pull requests
  - [x] commit messages are trimmed to the first line, sha to 7 characters
  - [x] 404 and 403 produce the friendly messages
- [x] Verify in the Inspector against a real repo (e.g. `pallets/flask`)
- [x] Add `github-analyzer` to the Claude Desktop config

### Done when

- [x] `uv run pytest tests/test_github.py` passes with no network access
- [x] "Is the fastapi/fastapi repo active, and what are the main open issues about?" uses all three tools and gives a sensible summary
- [x] A typo in the repo name produces the friendly error and Claude corrects itself or asks you
- [x] `git grep github_pat` finds nothing

### Stretch

- [ ] In-memory cache with a 5-minute TTL keyed by URL and params

---

## Phase 7: Docs RAG

**Goal:** semantic search over project documentation, returning passages with their source files.

**Why:** reuses your RAG skills, but here the server only **retrieves**. Claude (the client's model) writes the answer, so no LLM call happens inside the server.

### Files

- `docs/sample/*.md` (5 to 10 docs to index; can be this project's own docs)
- `servers/docs_rag/build_index.py`
- `servers/docs_rag/server.py`
- `tests/test_docs_rag.py`

### Tasks

- [x] Collect sample docs (e.g. setup, configuration, authentication, troubleshooting)
- [x] Write `build_index.py`:
  - [x] read all Markdown files in `docs/sample/`
  - [x] split into chunks of roughly 500 tokens with ~50 tokens overlap, preferring heading boundaries
  - [x] store in `chromadb.PersistentClient(path="data/chroma")`, collection `docs`, with metadata `{"source": filename}`
  - [x] delete and recreate the collection on each run
- [x] Write `server.py`:
  - [x] load the collection at startup; if missing, log "Run build_index.py first" to stderr
  - [x] `search_docs(query: str, top_k: int = 4)` with `top_k` clamped to `1..8`
  - [x] return `[{text, source, score}]`, score rounded to 3 decimals
  - [x] docstring tells the model to use it before answering doc questions and to cite the source
- [x] Write `tests/test_docs_rag.py` using a small temporary index:
  - [x] a query about a known topic returns the right source first
  - [x] `top_k` is respected and clamped
  - [x] empty query raises `ValueError` (raises `ToolError` instead — see note below)
- [x] Verify in the Inspector and add `docs-rag` to the Claude Desktop config

**Note:** the installed SDK is `mcp` 2.x (`MCPServer`, not the `FastMCP` shown in this
plan's code samples). Under 2.x a plain `ValueError` from a tool is masked as a generic
"Error executing tool" message; the client only sees the real message if the tool raises
`mcp.server.mcpserver.exceptions.ToolError` instead. `search_docs`/`query_collection` raise
`ToolError`, consistent with the fix already applied to `github_analyzer` in Phase 6.
`sql_explorer` (Phase 5) still raises plain `ValueError` and is scheduled to be fixed in
Phase 9. Verified Inspector-equivalent check: `uv run python -c "..."` driving the server
over real stdio via `mcp.client.stdio.stdio_client` — `search_docs` lists with the correct
schema, returns correctly cited passages, and both the empty-query and out-of-range-`top_k`
cases produce client-visible errors.

### Done when

- [x] `uv run servers/docs_rag/build_index.py` builds the index
- [x] `uv run pytest tests/test_docs_rag.py` passes
- [x] "How do I configure authentication?" gets an answer that cites the right file

---

## Phase 8: Resources and prompts

**Goal:** use all three MCP primitives, not just tools.

### Files

- `servers/sql_explorer/server.py`
- `servers/github_analyzer/server.py`

### Tasks

- [x] Add resource `schema://shop` to SQL Explorer: returns every table as `table(col type, ...)`, one per line
- [x] Add prompt `sales_report(month: str)` to SQL Explorer: asks for total revenue, top 5 products, top 5 customers and one insight for that month
- [x] Add prompt `analyse_repo(owner: str, repo: str)` to GitHub Analyzer: asks for activity level, main issue themes and a health verdict
- [x] Verify in the Inspector (**Resources** and **Prompts** tabs)
- [x] In Claude Desktop, attach `schema://shop` and pick each prompt from the menu

### Done when

- [x] The resource and both prompts appear and work in the Inspector and Claude Desktop
- [x] You can explain: the model calls tools; the user or app attaches resources; prompts are user-chosen templates

---

## Phase 9: Security hardening

**Goal:** make every server robust against bad input, abuse and prompt injection.

**Why:** the model chooses tool inputs and can be manipulated. This phase turns a demo into an engineering project.

### Files

- `common/limits.py`
- all `servers/*/server.py`
- `tests/test_security.py`

### Tasks

- [x] **Input validation:** convert tool parameters to `Annotated[..., Field(...)]`:
  - [x] GitHub `owner`: `pattern=r"^[A-Za-z0-9-]{1,39}$"` (already done in Phase 6)
  - [x] GitHub `repo`: `pattern=r"^[A-Za-z0-9._-]{1,100}$"` (already done in Phase 6)
  - [x] all `limit`/`top_k`: `ge`/`le` bounds (already done in Phases 5-7)
  - [x] `sql` and `query`: `max_length` (2000 and 500)
- [x] **Rate limiting:** finished `common/limits.py` with `RateLimiter.check()` (raises `ToolError` on top of the existing sliding-window `allow()`); applied `30 per 60s` (`github_limit`) to each GitHub tool and `60 per 60s` (`sql_limit`) to `run_readonly_query`
- [x] **Error hygiene:** `mcp` 2.x already wraps any exception that isn't a deliberate `ToolError`/`ResourceError`/`MCPError` as `UnexpectedToolError` with the generic client-visible message `"Error executing tool <name>"` and logs the full traceback server-side via `logger.exception(...)` (stderr); converted SQL Explorer's remaining plain `ValueError`s to `ToolError` so its own deliberate messages (e.g. "Unknown table: ...") reach the client instead of being masked
- [x] **Audit log:** `common/logging_setup.audit()` decorator (sync + async) logs tool name, arguments (redacted if the keyword name looks secret-ish), duration in ms and success/error; applied to all 7 tools across the three servers
- [x] **Prompt injection review:** confirmed no tool can write, send, post or delete anything; README security section already documents this
- [x] **Secrets check:** confirmed `GITHUB_TOKEN` is never logged or returned (tested); `.env` is gitignored
- [x] Write `tests/test_security.py`:
  - [x] invalid owner/repo names are rejected before any HTTP call
  - [x] out-of-range limits are rejected or clamped
  - [x] the rate limiter raises after the limit and recovers after the window
  - [x] error messages contain no file paths or tracebacks

### Done when

- [x] `uv run pytest` passes in full
- [x] The Inspector shows the patterns and bounds in each tool's schema
- [x] Logs show one audit line per tool call
- [x] You can explain each row of the README security table

---

## Phase 10: Remote HTTP transport and authentication

**Goal:** run any server as a web service, protected by an API key.

**Why:** stdio only works on the same machine. HTTP lets the server live in the cloud and be shared.

### Files

- `common/auth.py`
- all `servers/*/server.py` (`__main__` block)

### Tasks

- [x] Add `uvicorn` and `starlette` if not already installed (`uv add uvicorn starlette`)
- [x] Write `common/auth.py` with an `ApiKeyMiddleware` that returns `401 {"error": "unauthorized"}` unless `Authorization: Bearer <MCP_API_KEY>` matches; compare with `secrets.compare_digest`
- [x] Refuse to start in HTTP mode if `MCP_API_KEY` is missing or still `change-me` (`common/auth.require_api_key`, which also calls `load_dotenv()` itself since not every server's entry point does)
- [x] Update each server's `__main__`:
  ```python
  if __name__ == "__main__":
      if "--http" in sys.argv:
          require_api_key()
          app = mcp.streamable_http_app()
          app.add_middleware(ApiKeyMiddleware)
          uvicorn.run(app, host="0.0.0.0", port=8000)
      else:
          mcp.run()
  ```
- [x] Check the installed MCP SDK version for the exact HTTP app function name before relying on it (`mcp==2.3.0`, `MCPServer.streamable_http_app()`)
- [x] Test with curl: no header → 401; correct header → not 401 (confirmed against the real `.env` key with `sql_explorer`: wrong/missing key → 401; correct key → passes auth and reaches the real protocol handler)
- [x] Test in the Inspector with transport "Streamable HTTP", URL `http://localhost:8000/mcp`, and the auth header (first verified programmatically with a real `mcp.ClientSession` over `streamable_http_client` — `initialize()`, `list_tools()` → `list_tables`/`describe_table`/`run_readonly_query`, `call_tool("list_tables")` → `customers`/`products`/`orders`; then confirmed again in the actual Inspector GUI in a real browser tab, for all three servers running `--http` simultaneously: `sql_explorer` on :8000 (`list_tables` → `customers`/`products`/`orders`) and `docs_rag` on :8002 (`search_docs` → real passages from `authentication.md`/`configuration.md`), each with its own `streamable-http` entry and `Authorization: Bearer <key>` custom header)

### Done when

- [x] `uv run servers/sql_explorer/server.py --http` serves on port 8000
- [x] Requests without the key get 401; with the key, tools work in the Inspector (verified end-to-end: 401 without/with-wrong key via curl and in the Inspector GUI's own network log — including the Inspector's automatic OAuth discovery attempts getting 401'd — then a successful authenticated connection and tool call)
- [x] stdio mode still works unchanged in Claude Desktop (unit + protocol tests pass; `__main__` falls through to `mcp.run()` unchanged when `--http` is absent)

### Added beyond the plan

The plan didn't call for this, but it came up while testing side-by-side in the Inspector: all three servers hardcoded `port=8000`, so only one could run in `--http` mode at a time, which made it easy to accidentally query the wrong server (e.g. an Inspector entry labeled `github-analyzer` that was actually still talking to `sql_explorer` on :8000, with no error to signal the mismatch).

- Added `common/cli.py` (`http_port(default)`): reads an optional `--port <N>` CLI argument, else falls back to a default.
- Gave each server its own default port so they can all run in `--http` mode simultaneously without colliding: `sql_explorer` → 8000, `github_analyzer` → 8001, `docs_rag` → 8002 (still overridable per-run with `--port`).
- Added `tests/test_cli.py` (2 tests: default-port and explicit `--port`).
- Verified live: started `sql_explorer --http` (8000) and `github_analyzer --http` (8001) at the same time; both independently enforced the API key and answered on their own port.

---

## Phase 11: Automated testing and CI

**Goal:** prove every server works through the real protocol, and run all tests automatically on every push.

### Files

- `tests/test_protocol.py`
- `tests/e2e_questions.md`
- `.github/workflows/tests.yml`

### Tasks

- [x] Write `tests/test_protocol.py` using `StdioServerParameters`, `stdio_client` and `ClientSession`:
  - [x] for each server, `initialize()` then `list_tools()` and assert the expected tool names
  - [x] for SQL Explorer, `call_tool("run_readonly_query", {...})` returns rows
  - [x] for SQL Explorer, a `DROP TABLE` call returns an error result
- [x] Write `tests/e2e_questions.md` with 10 to 15 questions, expected tools and expected outcome, including:
  - "What was total revenue in October?"
  - "Which 5 customers spent the most?"
  - "Summarise open issues in pallets/flask"
  - "How do I configure authentication?"
  - "Delete all orders" (must be refused)
  (15 questions total, also covering stacked-statement/DDL rejection and a prompt-injection refusal — see the file)
- [ ] Run the e2e questions in Claude Desktop and record pass/fail — **manual, needs you**: I can't click through Claude Desktop myself
- [x] Write `.github/workflows/tests.yml`:
  - [x] trigger on push and pull request
  - [x] set up uv (`astral-sh/setup-uv@v3`), run `uv sync`, `uv run scripts/seed_db.py`, `uv run pytest`
  - [x] set a dummy `GITHUB_TOKEN` env var (tests are mocked) — also added a dummy `MCP_API_KEY`, needed since Phase 10 added that requirement after this plan was written
- [ ] Optional: add `ruff check` to the workflow — **skipped**: there's no `[tool.ruff]` config in this repo, and `uvx ruff check .` against its unconfigured defaults currently reports 23 pre-existing findings across the test suite. Adding it as a CI gate would fail the build over code this phase didn't touch; picking a ruleset and cleaning that up is a separate call for you to make, not mine to make unilaterally

### Done when

- [x] `uv run pytest` passes locally, including protocol tests (60/60, verified both normally and under a simulated CI environment — `.env` moved aside, only `GITHUB_TOKEN`/`MCP_API_KEY` set as plain env vars, matching what the workflow actually provides)
- [ ] The GitHub Actions run is green — **not yet run**: this needs a push to GitHub, which I won't do without you asking
- [ ] All e2e questions pass — pending your manual run of `tests/e2e_questions.md` in Claude Desktop

---

## Phase 12: Packaging, documentation and publishing

**Goal:** a repo that a recruiter understands in two minutes and anyone can run.

### Files

- `servers/{sql_explorer,github_analyzer,docs_rag}/Dockerfile`
- `README.md`
- `docs/demo.gif`

### Tasks

- [ ] Write a Dockerfile per server:
  ```dockerfile
  FROM python:3.12-slim
  RUN pip install uv
  WORKDIR /app
  COPY . .
  RUN uv sync --frozen && uv run scripts/seed_db.py
  EXPOSE 8000
  CMD ["uv", "run", "servers/sql_explorer/server.py", "--http"]
  ```
- [ ] Build and run each image with `--env-file .env`; confirm the HTTP endpoint works
- [ ] Add a `.dockerignore` (`.venv`, `.env`, `data/chroma`, `.git`)
- [ ] Update `README.md`:
  - [ ] replace `<your-username>` and `<your-profile>` placeholders
  - [ ] confirm every command in the README actually works on a fresh clone
  - [ ] confirm the tools table matches the real tool names
- [ ] Record a 2-minute demo (OBS): one question per server, then "Delete all orders" being refused
- [ ] Convert a short clip to `docs/demo.gif` and upload the full video to YouTube or LinkedIn
- [ ] Final review: `git grep -i token`, no secrets, no debug prints
- [ ] Tag a release `v1.0.0` on GitHub
- [ ] Optional: publish to PyPI so servers run with `uvx`
- [ ] Write a LinkedIn post about one lesson (e.g. two-layer SQL safety)

### Done when

- [ ] A fresh clone following only the README works end to end
- [ ] Docker images build and run
- [ ] The demo GIF shows at the top of the README
- [ ] Release `v1.0.0` exists
- [ ] Resume line added:
  > Built a toolkit of three secure MCP servers (Python, FastMCP) exposing read-only SQL, GitHub analytics and RAG document search to any MCP client, with input validation, rate limiting, API-key auth, Docker and CI-tested automated tests.

---

## Definition of done (whole project)

- [ ] All 13 phases ticked
- [ ] `uv run pytest` green locally and in CI
- [ ] All servers work in Claude Desktop (stdio) and in HTTP mode with auth
- [ ] No write or destructive tools exist anywhere
- [ ] README, CLAUDE.md and this plan are up to date
- [ ] Roadmap items in the README reflect what is left

## Suggested prompts for Claude Code

- "Read docs/BUILD_PLAN.md and start Phase 5. Do only the unticked tasks in that phase."
- "Phase 5 is done. Run the tests, tick the completed boxes and tell me what's left."
- "Review Phase 9 tasks against the current code and list anything missing."
