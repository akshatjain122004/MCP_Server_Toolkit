# Troubleshooting

## Tools don't appear in Claude Desktop

Check that the `command`/`args` in the Claude Desktop config use an
**absolute** path to the project directory, and that Claude Desktop was
fully quit (including the system tray icon) and reopened after editing the
config.

## "spawn uv ENOENT" in the logs

Claude Desktop could not find `uv` on its PATH. Use the full path to the
`uv` executable (found with `where uv` on Windows or `which uv` elsewhere)
as the `command` value instead of just `"uv"`.

## The connection closes immediately

Something was printed to stdout inside the server, or an import failed at
startup. Stdout carries the MCP protocol; any stray `print()` call corrupts
it. Check the server log for the real error, which is written to stderr.

## GitHub 403 errors

This usually means the GitHub API rate limit was reached, or `GITHUB_TOKEN`
does not have the required scopes. The server reports this as "GitHub rate
limit reached. Try again later."

## Docs RAG returns nothing useful

Run `uv run servers/docs_rag/build_index.py` to (re)build the index. If the
server logs "Docs index not found. Run build_index.py first," the index was
never built or `data/chroma/` was deleted.
