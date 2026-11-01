"""Phase 5: SQL explorer server — query the sample shop.db over MCP."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sql-explorer")

# TODO: tools for listing tables, describing schema, and running read-only
# queries against data/shop.db.

if __name__ == "__main__":
    mcp.run()
