"""Phase 2: practice server — minimal MCP server with a single tool."""

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("hello")


@mcp.tool()
def greet(name: str) -> str:
    """Return a friendly greeting for the given name."""
    return f"Hello, {name}!"


@mcp.tool()
def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b


if __name__ == "__main__":
    mcp.run()
