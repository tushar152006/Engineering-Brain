from app.models.schemas import SourceFile
from app.retrieval.chunker import chunk_source_file


def test_chunk_source_file_creates_cited_chunks() -> None:
    file = SourceFile(
        path="README.md",
        language="markdown",
        content="# Demo\n\nThis repository explains the engineering brain architecture.",
        size_bytes=64,
    )

    chunks = chunk_source_file("repo", file)

    assert len(chunks) == 1
    assert chunks[0].file_path == "README.md"
    assert chunks[0].start_line == 1
    assert chunks[0].chunk_type == "docs"

