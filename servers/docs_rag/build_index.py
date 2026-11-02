"""Phase 7: build the Chroma vector index over markdown docs."""

import re
import sys
from pathlib import Path

import chromadb

# Running this file directly (as Claude Desktop does) only puts this file's own
# directory on sys.path, so the project-root `common` package needs a hand.
_PROJECT_ROOT = str(Path(__file__).parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from common.logging_setup import get_logger  # noqa: E402

logger = get_logger("docs-rag-build-index")

DOCS_DIR = Path(__file__).parents[2] / "docs" / "sample"
CHROMA_PATH = Path(__file__).parents[2] / "data" / "chroma"
COLLECTION_NAME = "docs"

CHUNK_SIZE_WORDS = 500
CHUNK_OVERLAP_WORDS = 50

_HEADING_RE = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)


def _split_sections(text: str) -> list[str]:
    """Split markdown into sections, each starting at a heading line (if any)."""
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [text] if text.strip() else []

    sections = []
    if matches[0].start() > 0 and text[: matches[0].start()].strip():
        sections.append(text[: matches[0].start()])
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append(text[start:end])
    return sections


def chunk_markdown(
    text: str,
    chunk_size: int = CHUNK_SIZE_WORDS,
    overlap: int = CHUNK_OVERLAP_WORDS,
) -> list[str]:
    """Split markdown text into overlapping word-count chunks, preferring heading boundaries.

    Sections (heading to next heading) are never merged. A section longer than
    `chunk_size` words is split into overlapping sliding windows of `chunk_size`
    words, stepping by `chunk_size - overlap` words at a time.
    """
    chunks: list[str] = []
    step = chunk_size - overlap
    for section in _split_sections(text):
        words = section.split()
        if not words:
            continue
        if len(words) <= chunk_size:
            chunks.append(section.strip())
            continue
        for start in range(0, len(words), step):
            window = words[start : start + chunk_size]
            if not window:
                break
            chunks.append(" ".join(window))
            if start + chunk_size >= len(words):
                break
    return chunks


def build_index(docs_dir: Path, chroma_path: Path, collection_name: str = COLLECTION_NAME):
    """Read every *.md file in docs_dir, chunk it, and (re)build the Chroma collection."""
    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.create_collection(collection_name, metadata={"hnsw:space": "cosine"})

    ids, documents, metadatas = [], [], []
    for path in sorted(docs_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for i, chunk in enumerate(chunk_markdown(text)):
            ids.append(f"{path.name}:{i}")
            documents.append(chunk)
            metadatas.append({"source": path.name})

    if documents:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return collection


if __name__ == "__main__":
    index = build_index(DOCS_DIR, CHROMA_PATH)
    logger.info("Indexed %d chunks from %s into %s", index.count(), DOCS_DIR, CHROMA_PATH)
