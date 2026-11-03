"""Phase 7: docs RAG server — semantic search over project documentation.

Retrieval only: this server returns passages and their sources. The client's
model reads them and writes the answer; no LLM call happens in here.
"""

import sys
from pathlib import Path
from typing import Annotated

import chromadb
import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

# Running this file directly (as Claude Desktop does) only puts this file's own
# directory on sys.path, so the project-root `common` package needs a hand.
_PROJECT_ROOT = str(Path(__file__).parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from common.auth import ApiKeyMiddleware, require_api_key  # noqa: E402
from common.cli import http_port  # noqa: E402
from common.logging_setup import audit, get_logger  # noqa: E402

DEFAULT_HTTP_PORT = 8002

mcp = MCPServer("docs-rag")
logger = get_logger("docs-rag")

CHROMA_PATH = Path(__file__).parents[2] / "data" / "chroma"
COLLECTION_NAME = "docs"
MAX_TOP_K = 8
MAX_QUERY_LENGTH = 500


def _load_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception:
        logger.error("Docs index not found at %s. Run build_index.py first.", CHROMA_PATH)
        return None


_collection = _load_collection()


def query_collection(collection, query: str, top_k: int = 4) -> list[dict]:
    """Run the similarity search against a Chroma collection.

    Kept separate from the `search_docs` tool so tests can inject a small
    temporary collection instead of the real one loaded at server startup.
    """
    if not query or not query.strip():
        raise ToolError("query must not be empty.")
    if collection is None:
        raise ToolError("Docs index not found. Run build_index.py first.")

    clamped_top_k = max(1, min(top_k, MAX_TOP_K))
    result = collection.query(query_texts=[query.strip()], n_results=clamped_top_k)

    hits = []
    for doc, meta, distance in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        hits.append({"text": doc, "source": meta["source"], "score": round(1 - distance, 3)})
    return hits


@mcp.tool()
@audit(logger)
def search_docs(
    query: Annotated[str, Field(max_length=MAX_QUERY_LENGTH)],
    top_k: Annotated[int, Field(ge=1, le=MAX_TOP_K)] = 4,
) -> list[dict]:
    """Semantically search the project documentation and return the most relevant passages.

    Call this before answering any question about setup, configuration, authentication
    or troubleshooting, and cite each result's `source` file in your answer.
    """
    results = query_collection(_collection, query, top_k)
    logger.info("search_docs query=%r top_k=%d hits=%d", query, top_k, len(results))
    return results


if __name__ == "__main__":
    if "--http" in sys.argv:
        require_api_key()
        app = mcp.streamable_http_app()
        app.add_middleware(ApiKeyMiddleware)
        uvicorn.run(app, host="0.0.0.0", port=http_port(DEFAULT_HTTP_PORT))
    else:
        mcp.run()
