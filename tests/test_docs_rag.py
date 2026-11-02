import pytest
from mcp.server.mcpserver.exceptions import ToolError

from servers.docs_rag.build_index import build_index, chunk_markdown
from servers.docs_rag.server import MAX_TOP_K, query_collection


def _write(docs_dir, name, content):
    (docs_dir / name).write_text(content, encoding="utf-8")


def test_known_topic_returns_right_source_first(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    _write(
        docs_dir,
        "authentication.md",
        "# Authentication\n"
        "Set MCP_API_KEY in your .env file to enable bearer token authentication "
        "for the HTTP transport.",
    )
    _write(
        docs_dir,
        "setup.md",
        "# Setup\nInstall Python 3.10 or newer and uv, then run uv sync to install dependencies.",
    )
    _write(
        docs_dir,
        "troubleshooting.md",
        "# Troubleshooting\n"
        "If tools do not appear in Claude Desktop, check that the config path is absolute.",
    )

    collection = build_index(docs_dir, tmp_path / "chroma")

    results = query_collection(
        collection, "how do I configure authentication for the HTTP server", top_k=2
    )

    assert results[0]["source"] == "authentication.md"


def test_top_k_is_respected_and_clamped(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    for i in range(10):
        _write(docs_dir, f"doc{i}.md", f"# Topic {i}\nUnique filler content about topic number {i}.")

    collection = build_index(docs_dir, tmp_path / "chroma")

    assert len(query_collection(collection, "topic", top_k=3)) == 3
    assert len(query_collection(collection, "topic", top_k=100)) <= MAX_TOP_K


def test_empty_query_raises_tool_error(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    _write(docs_dir, "a.md", "# A\nSome content.")
    collection = build_index(docs_dir, tmp_path / "chroma")

    with pytest.raises(ToolError):
        query_collection(collection, "   ", top_k=4)


def test_chunk_markdown_splits_on_headings():
    text = "# One\nFirst section text.\n\n# Two\nSecond section text."
    chunks = chunk_markdown(text, chunk_size=500, overlap=50)
    assert len(chunks) == 2
    assert chunks[0].startswith("# One")
    assert chunks[1].startswith("# Two")


def test_chunk_markdown_splits_long_section_with_overlap():
    words = " ".join(f"word{i}" for i in range(1200))
    text = f"# Big\n{words}"
    chunks = chunk_markdown(text, chunk_size=500, overlap=50)
    assert len(chunks) == 3
    assert chunks[0].split()[-50:] == chunks[1].split()[:50]
