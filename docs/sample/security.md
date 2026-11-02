# Security

Every tool in this toolkit is read-only. There are no tools that write,
send, post or delete anything, in any server.

## Why two layers for SQL

The SQL Explorer validates that a query is a single `SELECT` or `WITH`
statement with no semicolons and no write/DDL keywords, and separately
opens the database connection itself in read-only mode
(`file:...?mode=ro`). Either layer alone would eventually be bypassed by a
clever enough query; together they hold even if one layer has a bug.

## Treating tool output as untrusted data

Issue bodies, commit messages and document text returned by a tool may
contain text that looks like instructions. Servers return this content as
plain data and never execute or act on it themselves. The model reading the
result is expected to treat it the same way: as data to reason about, not
as commands to follow.

## Rate limiting and input validation

Tool parameters such as `owner`, `repo`, `limit` and `top_k` are constrained
with patterns and numeric bounds, enforced both in the tool's schema and
again inside the function body. External API calls are additionally subject
to a sliding-window rate limiter.

## Secrets

`GITHUB_TOKEN` and `MCP_API_KEY` live only in `.env`, which is excluded from
git by `.gitignore`. Neither value is ever logged or returned in a tool
result.
