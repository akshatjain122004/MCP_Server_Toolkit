# Authentication

Authentication only matters when a server is exposed over HTTP; stdio mode
(the default, used by Claude Desktop) has no network surface and needs no
authentication at all.

## Setting up the API key

1. Set `MCP_API_KEY` in `.env` to a long random value. The placeholder value
   `change-me` is rejected on purpose.
2. Start the server with the `--http` flag, for example
   `uv run servers/sql_explorer/server.py --http`.
3. Every request must include an `Authorization: Bearer <MCP_API_KEY>` header.
   Requests without a valid key receive `401 {"error": "unauthorized"}`.

## How the check works

An `ApiKeyMiddleware` wraps the server's HTTP app and compares the header
value against `MCP_API_KEY` using `secrets.compare_digest`, which avoids
leaking timing information that could help guess the key.

## GitHub authentication

The GitHub Analyzer authenticates to the GitHub REST API using
`GITHUB_TOKEN`, sent as an `Authorization: Bearer <token>` header on every
request. This token should be fine-grained and read-only; the server never
writes to GitHub.
