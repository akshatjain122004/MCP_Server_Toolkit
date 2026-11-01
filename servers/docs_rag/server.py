"""Phase 7: docs RAG server — retrieval-augmented Q&A over MCP."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("docs-rag")

# TODO: tools for indexing documents and answering questions via
# retrieval-augmented generation.

if __name__ == "__main__":
    mcp.run()
