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
| 5 | SQL Explorer | 3 read-only DB tools | 3 days | ⬜ |
| 6 | GitHub Analyzer | 3 async API tools | 3 days | ⬜ |
| 7 | Docs RAG | Index + `search_docs` | 3 days | ⬜ |
| 8 | Resources and prompts | `schema://shop`, 2 prompts | 0.5 day | ⬜ |
| 9 | Security hardening | Validation, rate limits, audit log | 1.5 days | ⬜ |
| 10 | Remote HTTP + auth | `--http` mode with API key | 1 day | ⬜ |
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
- [ ] Write `scripts/seed_db.py` that creates `data/shop.db` with:
  - `customers(id, name, email, city, created_at)`, about 60 rows, cities such as Jaipur, Udaipur, Delhi, Mumbai, Bengaluru
  - `products(id, name, category, price)`, about 20 rows
  - `orders(id, customer_id, product_id, quantity, total, order_date)`, about 300 rows spread over the last 6 months
  - Use `Faker` with a fixed seed (`Faker.seed(42)`) so data is the same on every run
  - Delete and recreate the file each run so it is idempotent
- [ ] Add the MIT `LICENSE`
- [ ] `git init`, first commit

### Done when

- [ ] `uv sync` succeeds on a fresh clone
- [ ] `uv run scripts/seed_db.py` creates `data/shop.db`
- [ ] `sqlite3 data/shop.db "SELECT COUNT(*) FROM orders"` returns about 300
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

- [ ] Set constants: `DB_PATH = Path(__file__).parents[2] / "data" / "shop.db"`, `MAX_ROWS = 100`
- [ ] Write `connect()` opening `f"file:{DB_PATH}?mode=ro"` with `uri=True`, `timeout=5`, and `row_factory = sqlite3.Row`
- [ ] Implement `list_tables` (query `sqlite_master` where `type='table'`, exclude `sqlite_%` tables)
- [ ] Implement `describe_table`:
  - [ ] reject any table name not returned by `list_tables` with a helpful `ValueError`
  - [ ] return `PRAGMA table_info` as `{name, type}` pairs
- [ ] Implement `run_readonly_query` with **layer 1 validation**:
  - [ ] strip whitespace and one trailing `;`
  - [ ] must start with `select` or `with` (case-insensitive)
  - [ ] reject any remaining `;` (stacked statements)
  - [ ] reject keywords with word boundaries: `insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum`
  - [ ] clamp `limit` to `1..MAX_ROWS`
  - [ ] wrap as `SELECT * FROM (<sql>) LIMIT ?`
- [ ] Keep **layer 2**: the read-only connection, even though validation exists
- [ ] Add a query timeout with `conn.set_progress_handler` (abort after ~5 seconds)
- [ ] Log every query to stderr via `common/logging_setup.py`
- [ ] Write clear docstrings (what, limits, when to use), e.g. "Call list_tables first"
- [ ] Write `tests/test_sql.py`:
  - [ ] `list_tables` returns the three tables
  - [ ] `describe_table("customers")` includes `city`
  - [ ] `describe_table("users; --")` raises `ValueError`
  - [ ] a valid SELECT returns rows
  - [ ] a `WITH ... SELECT` query works
  - [ ] row cap: `limit=5000` returns at most 100 rows
  - [ ] parametrised attacks all raise `ValueError`: `DROP TABLE customers`, `DELETE FROM orders`, `SELECT 1; DROP TABLE customers`, `select * from customers; update orders set total=0`, `PRAGMA table_info(customers)`, `ATTACH DATABASE 'x.db' AS x`
  - [ ] column names containing keywords (e.g. `created_at`) still work
- [ ] Verify all three tools in the Inspector
- [ ] Add `sql-explorer` to the Claude Desktop config

### Done when

- [ ] `uv run pytest tests/test_sql.py` passes
- [ ] In Claude Desktop, "Which city has the most customers?" is answered correctly via `list_tables` → `describe_table` → `run_readonly_query`
- [ ] "Delete all orders" is refused and `orders` still has all rows
- [ ] You can explain why there are two safety layers

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

- [ ] Put your token in `.env` as `GITHUB_TOKEN=...`; load it with `python-dotenv`
- [ ] Fail fast at startup with a clear stderr log if `GITHUB_TOKEN` is missing
- [ ] Write an async helper `gh(path, params)` using `httpx.AsyncClient(timeout=10)` with headers `Authorization: Bearer <token>` and `Accept: application/vnd.github+json`
- [ ] Map errors to friendly `ValueError`s:
  - [ ] 404 → "Repository not found. Check owner and repo name."
  - [ ] 403/429 → "GitHub rate limit reached. Try again later."
  - [ ] timeout → "GitHub did not respond in time."
- [ ] Implement the three tools as `async def`, each returning only the fields in the table above
- [ ] Filter out items with a `pull_request` key in `list_open_issues`
- [ ] Clamp `limit` to `1..30`
- [ ] Write `tests/test_github.py` with `respx` mocks (no real network):
  - [ ] summary returns exactly the expected keys
  - [ ] issues exclude pull requests
  - [ ] commit messages are trimmed to the first line, sha to 7 characters
  - [ ] 404 and 403 produce the friendly messages
- [ ] Verify in the Inspector against a real repo (e.g. `pallets/flask`)
- [ ] Add `github-analyzer` to the Claude Desktop config

### Done when

- [ ] `uv run pytest tests/test_github.py` passes with no network access
- [ ] "Is the fastapi/fastapi repo active, and what are the main open issues about?" uses all three tools and gives a sensible summary
- [ ] A typo in the repo name produces the friendly error and Claude corrects itself or asks you
- [ ] `git grep github_pat` finds nothing

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

- [ ] Collect sample docs (e.g. setup, configuration, authentication, troubleshooting)
- [ ] Write `build_index.py`:
  - [ ] read all Markdown files in `docs/sample/`
  - [ ] split into chunks of roughly 500 tokens with ~50 tokens overlap, preferring heading boundaries
  - [ ] store in `chromadb.PersistentClient(path="data/chroma")`, collection `docs`, with metadata `{"source": filename}`
  - [ ] delete and recreate the collection on each run
- [ ] Write `server.py`:
  - [ ] load the collection at startup; if missing, log "Run build_index.py first" to stderr
  - [ ] `search_docs(query: str, top_k: int = 4)` with `top_k` clamped to `1..8`
  - [ ] return `[{text, source, score}]`, score rounded to 3 decimals
  - [ ] docstring tells the model to use it before answering doc questions and to cite the source
- [ ] Write `tests/test_docs_rag.py` using a small temporary index:
  - [ ] a query about a known topic returns the right source first
  - [ ] `top_k` is respected and clamped
  - [ ] empty query raises `ValueError`
- [ ] Verify in the Inspector and add `docs-rag` to the Claude Desktop config

### Done when

- [ ] `uv run servers/docs_rag/build_index.py` builds the index
- [ ] `uv run pytest tests/test_docs_rag.py` passes
- [ ] "How do I configure authentication?" gets an answer that cites the right file

---

## Phase 8: Resources and prompts

**Goal:** use all three MCP primitives, not just tools.

### Files

- `servers/sql_explorer/server.py`
- `servers/github_analyzer/server.py`

### Tasks

- [ ] Add resource `schema://shop` to SQL Explorer: returns every table as `table(col type, ...)`, one per line
- [ ] Add prompt `sales_report(month: str)` to SQL Explorer: asks for total revenue, top 5 products, top 5 customers and one insight for that month
- [ ] Add prompt `analyse_repo(owner: str, repo: str)` to GitHub Analyzer: asks for activity level, main issue themes and a health verdict
- [ ] Verify in the Inspector (**Resources** and **Prompts** tabs)
- [ ] In Claude Desktop, attach `schema://shop` and pick each prompt from the menu

### Done when

- [ ] The resource and both prompts appear and work in the Inspector and Claude Desktop
- [ ] You can explain: the model calls tools; the user or app attaches resources; prompts are user-chosen templates

---

## Phase 9: Security hardening

**Goal:** make every server robust against bad input, abuse and prompt injection.

**Why:** the model chooses tool inputs and can be manipulated. This phase turns a demo into an engineering project.

### Files

- `common/limits.py`
- all `servers/*/server.py`
- `tests/test_security.py`

### Tasks

- [ ] **Input validation:** convert tool parameters to `Annotated[..., Field(...)]`:
  - [ ] GitHub `owner`: `pattern=r"^[A-Za-z0-9-]{1,39}$"`
  - [ ] GitHub `repo`: `pattern=r"^[A-Za-z0-9._-]{1,100}$"`
  - [ ] all `limit`/`top_k`: `ge`/`le` bounds
  - [ ] `sql` and `query`: `max_length` (e.g. 2000 and 500)
- [ ] **Rate limiting:** finish `common/limits.py` with a sliding-window `RateLimiter(max_calls, per_seconds)`; apply `30 per 60s` to each GitHub tool and `60 per 60s` to SQL queries
- [ ] **Error hygiene:** wrap unexpected exceptions so the client sees "Internal error, see server logs" while the full traceback goes to stderr
- [ ] **Audit log:** a small decorator or helper that logs tool name, arguments (never secrets), duration in ms and success/error for every call
- [ ] **Prompt injection review:** confirm no tool can write, send, post or delete anything; add a note to the README security section
- [ ] **Secrets check:** confirm tokens are never logged or returned; `.env` is gitignored
- [ ] Write `tests/test_security.py`:
  - [ ] invalid owner/repo names are rejected before any HTTP call
  - [ ] out-of-range limits are rejected or clamped
  - [ ] the rate limiter raises after the limit and recovers after the window
  - [ ] error messages contain no file paths or tracebacks

### Done when

- [ ] `uv run pytest` passes in full
- [ ] The Inspector shows the patterns and bounds in each tool's schema
- [ ] Logs show one audit line per tool call
- [ ] You can explain each row of the README security table

---

## Phase 10: Remote HTTP transport and authentication

**Goal:** run any server as a web service, protected by an API key.

**Why:** stdio only works on the same machine. HTTP lets the server live in the cloud and be shared.

### Files

- `common/auth.py`
- all `servers/*/server.py` (`__main__` block)

### Tasks

- [ ] Add `uvicorn` and `starlette` if not already installed (`uv add uvicorn starlette`)
- [ ] Write `common/auth.py` with an `ApiKeyMiddleware` that returns `401 {"error": "unauthorized"}` unless `Authorization: Bearer <MCP_API_KEY>` matches; compare with `secrets.compare_digest`
- [ ] Refuse to start in HTTP mode if `MCP_API_KEY` is missing or still `change-me`
- [ ] Update each server's `__main__`:
  ```python
  if __name__ == "__main__":
      if "--http" in sys.argv:
          app = mcp.streamable_http_app()
          app.add_middleware(ApiKeyMiddleware)
          uvicorn.run(app, host="0.0.0.0", port=8000)
      else:
          mcp.run()
  ```
- [ ] Check the installed MCP SDK version for the exact HTTP app function name before relying on it
- [ ] Test in the Inspector with transport "Streamable HTTP", URL `http://localhost:8000/mcp`, and the auth header
- [ ] Test with curl: no header → 401; correct header → not 401

### Done when

- [ ] `uv run servers/sql_explorer/server.py --http` serves on port 8000
- [ ] Requests without the key get 401; with the key, tools work in the Inspector
- [ ] stdio mode still works unchanged in Claude Desktop

---

## Phase 11: Automated testing and CI

**Goal:** prove every server works through the real protocol, and run all tests automatically on every push.

### Files

- `tests/test_protocol.py`
- `tests/e2e_questions.md`
- `.github/workflows/tests.yml`

### Tasks

- [ ] Write `tests/test_protocol.py` using `StdioServerParameters`, `stdio_client` and `ClientSession`:
  - [ ] for each server, `initialize()` then `list_tools()` and assert the expected tool names
  - [ ] for SQL Explorer, `call_tool("run_readonly_query", {...})` returns rows
  - [ ] for SQL Explorer, a `DROP TABLE` call returns an error result
- [ ] Write `tests/e2e_questions.md` with 10 to 15 questions, expected tools and expected outcome, including:
  - "What was total revenue in October?"
  - "Which 5 customers spent the most?"
  - "Summarise open issues in pallets/flask"
  - "How do I configure authentication?"
  - "Delete all orders" (must be refused)
- [ ] Run the e2e questions in Claude Desktop and record pass/fail
- [ ] Write `.github/workflows/tests.yml`:
  - [ ] trigger on push and pull request
  - [ ] set up uv, run `uv sync`, `uv run scripts/seed_db.py`, `uv run pytest`
  - [ ] set a dummy `GITHUB_TOKEN` env var (tests are mocked)
- [ ] Optional: add `ruff check` to the workflow

### Done when

- [ ] `uv run pytest` passes locally, including protocol tests
- [ ] The GitHub Actions run is green
- [ ] All e2e questions pass

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
