# Configuration

All configuration for this toolkit is done through environment variables,
loaded from a local `.env` file. Never commit `.env`; only `.env.example`
(with placeholder values) is tracked in git.

## Environment variables

| Variable | Used by | Purpose |
| --- | --- | --- |
| `GITHUB_TOKEN` | GitHub Analyzer | A fine-grained personal access token with read-only access to public repositories |
| `MCP_API_KEY` | Any server run with `--http` | The bearer token clients must send to use the server remotely |

## Connecting a server to Claude Desktop

Open **Settings → Developer → Edit Config** in Claude Desktop and add an
entry under `mcpServers` with the absolute path to the project directory.
Claude Desktop must be fully quit and reopened (including the system tray
icon) before a new or changed server configuration takes effect.

## Database configuration

The SQL Explorer server always points at `data/shop.db`, opened in read-only
mode. There is no configuration option to point it at a different database;
this is a deliberate safety constraint, not an oversight.
