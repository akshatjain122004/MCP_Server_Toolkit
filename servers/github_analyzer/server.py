"""Phase 6: GitHub analyzer server — repo/PR/issue insights over MCP."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("github-analyzer")

# TODO: tools wrapping the GitHub API (via httpx) to inspect repos,
# pull requests, and issues. Requires a GITHUB_TOKEN in .env.

if __name__ == "__main__":
    mcp.run()
