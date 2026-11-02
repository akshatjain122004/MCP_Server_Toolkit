# Setup

This project requires Python 3.10 or newer and the `uv` package manager.

## Installing dependencies

Clone the repository, then run `uv sync` from the project root. This creates
a virtual environment and installs every runtime and development dependency
listed in `pyproject.toml`.

## Preparing sample data

Two generated data sources are needed before the servers are useful:

- `uv run scripts/seed_db.py` creates `data/shop.db`, a small SQLite database
  with fake customers, products and orders.
- `uv run servers/docs_rag/build_index.py` builds the vector index used by
  the Docs RAG server, reading every Markdown file in `docs/sample/`.

## Running a server

Each server is started with `uv run servers/<name>/server.py`. By default it
listens on stdio, which is how Claude Desktop talks to it. A server that
starts and waits silently, with no output and no crash, is working correctly.
