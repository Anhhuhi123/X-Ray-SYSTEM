from pathlib import Path

import pytest

from app.tasks import nfd_docs_indexer as indexer

pytestmark = pytest.mark.unit


class _FakeChunk:
    def __init__(self, text: str):
        self.text = text


class _FakeChunker:
    def __init__(self, texts: list[str]):
        self._texts = texts

    def chunk(self, content: str):
        return [_FakeChunk(text) for text in self._texts]


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, existing_docs=None):
        self.existing_docs = existing_docs or []
        self.added = []
        self.deleted = []
        self.committed = False
        self.executed = []

    async def execute(self, stmt):
        self.executed.append(stmt)
        return _FakeResult(self.existing_docs)

    def add(self, obj):
        self.added.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.committed = True


def test_get_docs_for_rag_folder_name_extracts_top_level_folder():
    file_path = Path(
        "/Users/macbook/Desktop/Sales_Kyanon/SurfSense/nbd_web/content/docs_for_RAG/Atelectasis/Atelectasis.docx"
    )

    assert indexer.get_docs_for_rag_folder_name(file_path) == "Atelectasis"


def test_generate_nfd_docs_content_hash_changes_when_prefix_is_included():
    content = b"example bytes"

    plain_hash = indexer.generate_nfd_docs_content_hash(content)
    prefixed_hash = indexer.generate_nfd_docs_content_hash(
        content,
        prefix_label="Atelectasis",
    )

    assert plain_hash != prefixed_hash


def test_create_nfd_docs_chunks_prefixes_folder_name(monkeypatch):
    monkeypatch.setattr(indexer.config, "chunker_instance", _FakeChunker(["chunk body"]))
    monkeypatch.setattr(indexer, "embed_text", lambda text: [len(text)])

    chunks = indexer.create_nfd_docs_chunks(
        "source content",
        prefix_label="Atelectasis",
    )

    assert len(chunks) == 1
    assert chunks[0].content == "Atelectasis :\n\nchunk body"
    assert chunks[0].embedding == [25]


@pytest.mark.asyncio
async def test_index_nfd_docs_prefixes_chunks_for_docs_for_rag(monkeypatch, tmp_path):
    docs_root = tmp_path / "content" / "docs_for_RAG" / "Atelectasis"
    docs_root.mkdir(parents=True)
    doc_file = docs_root / "Atelectasis.docx"
    doc_file.write_bytes(b"docx-bytes")

    monkeypatch.setattr(indexer, "CONTENT_DIR", tmp_path / "content")
    monkeypatch.setattr(indexer, "DOCS_FOR_RAG_DIR", tmp_path / "content" / "docs_for_RAG")
    monkeypatch.setattr(indexer, "get_all_indexable_files", lambda: [doc_file])
    monkeypatch.setattr(indexer, "parse_file_to_markdown", lambda *args, **kwargs: _async_return(("document body", "DOCLING")))
    monkeypatch.setattr(indexer, "embed_text", lambda text: [len(text)])
    monkeypatch.setattr(indexer.config, "chunker_instance", _FakeChunker(["chunk body"]))

    session = _FakeSession()

    created, updated, skipped, deleted = await indexer.index_nfd_docs(session)

    assert (created, updated, skipped, deleted) == (1, 0, 0, 0)
    assert session.committed is True
    assert len(session.added) == 1
    assert session.added[0].title == "Atelectasis"
    assert session.added[0].chunks[0].content == "Atelectasis :\n\nchunk body"


async def _async_return(value):
    return value
