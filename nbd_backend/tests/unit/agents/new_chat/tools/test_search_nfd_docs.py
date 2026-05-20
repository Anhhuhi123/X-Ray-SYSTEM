from unittest.mock import AsyncMock

import pytest

from app.agents.new_chat.tools import search_nfd_docs as nfd_search
from app.retriever import nfd_docs_hybrid_search as nfd_hybrid

pytestmark = pytest.mark.unit


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.executed_statements = []

    async def execute(self, stmt):
        self.executed_statements.append(stmt)
        return _FakeResult(self.rows)


@pytest.mark.asyncio
async def test_search_nfd_docs_async_uses_browse_fallback_for_degenerate_query(monkeypatch):
    browse_mock = AsyncMock(
        return_value=[
            {
                "document": {
                    "id": "doc-1",
                    "title": "NFD Overview",
                    "document_type": "NFD_DOCS",
                    "metadata": {"source": "docs/overview.mdx"},
                },
                "chunks": [{"chunk_id": "doc-11", "content": "overview"}],
                "source": "NFD_DOCS",
            }
        ]
    )
    def format_mock(*args, **kwargs):
        return "formatted"

    monkeypatch.setattr(nfd_search, "_browse_recent_nfd_docs", browse_mock)
    monkeypatch.setattr(nfd_search, "_compute_tool_output_budget", lambda _: 12345)
    monkeypatch.setattr(nfd_search, "format_documents_for_context", format_mock)

    session = _FakeSession(rows=[])
    result = await nfd_search.search_nfd_docs_async(
        query="*",
        db_session=session,
        top_k=5,
        max_input_tokens=2048,
    )

    assert result == "formatted"
    browse_mock.assert_awaited_once_with(top_k=5, start_date=None, end_date=None)


@pytest.mark.asyncio
async def test_search_nfd_docs_async_uses_combined_rrf_results(monkeypatch):
    hybrid_results = [
        {
            "document_id": 2,
            "document": {
                "id": "doc-2",
                "title": "Second",
                "document_type": "NFD_DOCS",
                "metadata": {"source": "docs/second.mdx"},
            },
            "chunks": [{"chunk_id": "doc-21", "content": "second"}],
            "source": "NFD_DOCS",
            "score": 0.03,
        }
    ]

    captured_kwargs = {}

    async def fake_combined(**kwargs):
        captured_kwargs.update(kwargs)
        return hybrid_results

    format_calls = {}

    def fake_format_documents_for_context(documents, *, max_chars, max_chunks_per_doc=0):
        format_calls["documents"] = documents
        format_calls["max_chars"] = max_chars
        format_calls["max_chunks_per_doc"] = max_chunks_per_doc
        return "formatted"

    monkeypatch.setattr(nfd_search, "combined_nfd_docs_rrf_search", fake_combined)
    monkeypatch.setattr(nfd_search, "format_documents_for_context", fake_format_documents_for_context)
    monkeypatch.setattr(nfd_search, "_compute_tool_output_budget", lambda _: 777)
    monkeypatch.setattr(nfd_search, "embed_text", lambda query: [0.1])

    result = await nfd_search.search_nfd_docs_async(
        query="how to use NFD",
        db_session=_FakeSession(rows=[]),
        top_k=10,
        max_input_tokens=4096,
    )

    assert result == "formatted"
    assert captured_kwargs["query_embedding"] == [0.1]
    assert format_calls["documents"] == hybrid_results
    assert format_calls["max_chars"] == 777


@pytest.mark.asyncio
async def test_combined_nfd_docs_rrf_search_ranks_doc_and_chunk_signals(monkeypatch):
    doc_results = [
        {
            "document_id": 1,
            "document": {
                "id": "doc-1",
                "title": "Alpha",
                "document_type": "NFD_DOCS",
                "metadata": {"source": "docs/alpha.mdx"},
            },
            "chunks": [{"chunk_id": "doc-11", "content": "alpha"}],
            "source": "NFD_DOCS",
            "score": 0.10,
        },
        {
            "document_id": 2,
            "document": {
                "id": "doc-2",
                "title": "Beta",
                "document_type": "NFD_DOCS",
                "metadata": {"source": "docs/beta.mdx"},
            },
            "chunks": [{"chunk_id": "doc-21", "content": "beta"}],
            "source": "NFD_DOCS",
            "score": 0.08,
        },
    ]
    chunk_results = [
        {
            "document_id": 2,
            "document": {
                "id": "doc-2",
                "title": "Beta",
                "document_type": "NFD_DOCS",
                "metadata": {"source": "docs/beta.mdx"},
            },
            "chunks": [{"chunk_id": "doc-21", "content": "beta"}],
            "source": "NFD_DOCS",
            "score": 0.20,
        },
        {
            "document_id": 3,
            "document": {
                "id": "doc-3",
                "title": "Gamma",
                "document_type": "NFD_DOCS",
                "metadata": {"source": "docs/gamma.mdx"},
            },
            "chunks": [{"chunk_id": "doc-31", "content": "gamma"}],
            "source": "NFD_DOCS",
            "score": 0.17,
        },
        {
            "document_id": 1,
            "document": {
                "id": "doc-1",
                "title": "Alpha",
                "document_type": "NFD_DOCS",
                "metadata": {"source": "docs/alpha.mdx"},
            },
            "chunks": [{"chunk_id": "doc-11", "content": "alpha"}],
            "source": "NFD_DOCS",
            "score": 0.15,
        },
    ]

    async def fake_documents_hybrid(*args, **kwargs):
        return doc_results

    async def fake_chunks_hybrid(*args, **kwargs):
        return chunk_results

    monkeypatch.setattr(nfd_hybrid, "_search_nfd_documents_hybrid", fake_documents_hybrid)
    monkeypatch.setattr(nfd_hybrid, "_search_nfd_chunks_hybrid", fake_chunks_hybrid)
    monkeypatch.setattr(nfd_hybrid, "embed_text", lambda query: [0.1])

    merged = await nfd_hybrid.combined_nfd_docs_rrf_search(
        query_text="setup guide",
        db_session=_FakeSession(rows=[]),
        top_k=2,
    )

    assert [item["document_id"] for item in merged] == [2, 1]
    assert merged[0]["score"] > merged[1]["score"]
