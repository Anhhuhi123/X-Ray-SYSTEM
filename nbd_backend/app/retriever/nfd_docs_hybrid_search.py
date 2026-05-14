"""Hybrid/RRF search for NFD documentation.

This module mirrors the KB retrieval shape, but operates only on the
NFD docs tables:
- nfd_docs_documents
- nfd_docs_chunks

It combines document-level and chunk-level hybrid search signals and fuses
them with Reciprocal Rank Fusion (RRF).
"""

import asyncio
import time
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import NFDDocsChunks, NFDDocsDocument, async_session_maker
from app.utils.document_converters import embed_text
from app.utils.perf import get_perf_logger

_RRF_CONSTANT = 60
_MAX_FETCH_CHUNKS_PER_DOC = 30


def _make_document_payload(doc_id: int, title: str, source: str) -> dict[str, Any]:
    return {
        "id": f"doc-{doc_id}",
        "title": title,
        "document_type": "NFD_DOCS",
        "metadata": {"source": source},
    }


def _doc_id_from_result(item: dict[str, Any]) -> int | None:
    doc_id = item.get("document_id")
    if doc_id is not None:
        try:
            return int(doc_id)
        except (TypeError, ValueError):
            return None

    document = item.get("document") or {}
    raw_id = document.get("id")
    if isinstance(raw_id, int):
        return raw_id
    if isinstance(raw_id, str) and raw_id.startswith("doc-"):
        try:
            return int(raw_id.removeprefix("doc-"))
        except ValueError:
            return None
    try:
        return int(raw_id)
    except (TypeError, ValueError):
        return None


async def _fetch_chunks_for_documents(
    db_session: AsyncSession,
    doc_ids: list[int],
) -> dict[int, list[dict[str, Any]]]:
    if not doc_ids:
        return {}

    chunk_query = (
        select(NFDDocsChunks)
        .options(joinedload(NFDDocsChunks.document))
        .where(NFDDocsChunks.document_id.in_(doc_ids))
        .order_by(NFDDocsChunks.document_id, NFDDocsChunks.id)
    )
    chunk_result = await db_session.execute(chunk_query)
    raw_chunks = chunk_result.scalars().all()

    doc_chunk_counts: dict[int, int] = {}
    chunks_by_doc: dict[int, list[dict[str, Any]]] = {doc_id: [] for doc_id in doc_ids}

    for chunk in raw_chunks:
        doc_id = chunk.document_id
        count = doc_chunk_counts.get(doc_id, 0)
        if count < _MAX_FETCH_CHUNKS_PER_DOC:
            chunks_by_doc.setdefault(doc_id, []).append(
                {"chunk_id": f"doc-{chunk.id}", "content": chunk.content}
            )
            doc_chunk_counts[doc_id] = count + 1

    return chunks_by_doc


def _merge_rrf_results(
    primary_results: list[dict[str, Any]],
    secondary_results: list[dict[str, Any]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    def _build_ranks(results: list[dict[str, Any]]) -> dict[int, int]:
        ranks: dict[int, int] = {}
        for rank, item in enumerate(results, start=1):
            doc_id = _doc_id_from_result(item)
            if doc_id is None or doc_id in ranks:
                continue
            ranks[doc_id] = rank
        return ranks

    primary_ranks = _build_ranks(primary_results)
    secondary_ranks = _build_ranks(secondary_results)

    all_doc_ids = set(primary_ranks) | set(secondary_ranks)
    if not all_doc_ids:
        return []

    merged_scores: dict[int, float] = {}
    for doc_id in all_doc_ids:
        score = 0.0
        primary_rank = primary_ranks.get(doc_id)
        secondary_rank = secondary_ranks.get(doc_id)
        if primary_rank is not None:
            score += 1.0 / (_RRF_CONSTANT + primary_rank)
        if secondary_rank is not None:
            score += 1.0 / (_RRF_CONSTANT + secondary_rank)
        merged_scores[doc_id] = score

    merged_data: dict[int, dict[str, Any]] = {}
    for result in primary_results:
        doc_id = _doc_id_from_result(result)
        if doc_id is not None and doc_id not in merged_data:
            merged_data[doc_id] = result
    for result in secondary_results:
        doc_id = _doc_id_from_result(result)
        if doc_id is not None and doc_id not in merged_data:
            merged_data[doc_id] = result

    sorted_doc_ids = sorted(all_doc_ids, key=lambda doc_id: merged_scores[doc_id], reverse=True)
    combined_results: list[dict[str, Any]] = []
    for doc_id in sorted_doc_ids[:top_k]:
        entry = merged_data[doc_id].copy()
        entry["document_id"] = doc_id
        entry["score"] = merged_scores[doc_id]
        combined_results.append(entry)

    return combined_results


async def _search_nfd_documents_hybrid(
    query_text: str,
    db_session: AsyncSession,
    top_k: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    query_embedding: list[float] | None = None,
) -> list[dict[str, Any]]:
    perf = get_perf_logger()
    t0 = time.perf_counter()

    if query_embedding is None:
        t_embed = time.perf_counter()
        query_embedding = await asyncio.to_thread(embed_text, query_text)
        perf.info(
            "[nfd_doc_search] document embedding in %.3fs",
            time.perf_counter() - t_embed,
        )

    tsvector = func.to_tsvector("english", NFDDocsDocument.content)
    tsquery = func.plainto_tsquery("english", query_text)
    base_conditions = []
    if start_date is not None:
        base_conditions.append(NFDDocsDocument.updated_at >= start_date)
    if end_date is not None:
        base_conditions.append(NFDDocsDocument.updated_at <= end_date)

    n_results = top_k * 2

    semantic_search_cte = (
        select(
            NFDDocsDocument.id,
            func.rank().over(order_by=NFDDocsDocument.embedding.op("<=>")(query_embedding)).label("rank"),
        )
        .where(*base_conditions)
        .order_by(NFDDocsDocument.embedding.op("<=>")(query_embedding))
        .limit(n_results)
        .cte("nfd_doc_semantic_search")
    )

    keyword_search_cte = (
        select(
            NFDDocsDocument.id,
            func.rank().over(order_by=func.ts_rank_cd(tsvector, tsquery).desc()).label("rank"),
        )
        .where(*base_conditions)
        .where(tsvector.op("@@")(tsquery))
        .order_by(func.ts_rank_cd(tsvector, tsquery).desc())
        .limit(n_results)
        .cte("nfd_doc_keyword_search")
    )

    final_query = (
        select(
            NFDDocsDocument,
            (
                func.coalesce(1.0 / (_RRF_CONSTANT + semantic_search_cte.c.rank), 0.0)
                + func.coalesce(1.0 / (_RRF_CONSTANT + keyword_search_cte.c.rank), 0.0)
            ).label("score"),
        )
        .select_from(
            semantic_search_cte.outerjoin(
                keyword_search_cte,
                semantic_search_cte.c.id == keyword_search_cte.c.id,
                full=True,
            )
        )
        .join(
            NFDDocsDocument,
            NFDDocsDocument.id
            == func.coalesce(semantic_search_cte.c.id, keyword_search_cte.c.id),
        )
        .order_by(text("score DESC"))
        .limit(top_k)
    )

    result = await db_session.execute(final_query)
    documents_with_scores = result.all()
    if not documents_with_scores:
        return []

    doc_ids = [doc.id for doc, _score in documents_with_scores]
    chunks_by_doc = await _fetch_chunks_for_documents(db_session, doc_ids)

    final_docs: list[dict[str, Any]] = []
    for doc, score in documents_with_scores:
        chunks_list = chunks_by_doc.get(doc.id, [])
        final_docs.append(
            {
                "document_id": doc.id,
                "content": "\n\n".join(c["content"] for c in chunks_list if c.get("content")),
                "score": float(score),
                "chunks": chunks_list,
                "document": _make_document_payload(doc.id, doc.title, doc.source),
                "source": "NFD_DOCS",
            }
        )

    perf.info(
        "[nfd_doc_search] document hybrid in %.3fs docs=%d",
        time.perf_counter() - t0,
        len(final_docs),
    )
    return final_docs


async def _search_nfd_chunks_hybrid(
    query_text: str,
    db_session: AsyncSession,
    top_k: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    query_embedding: list[float] | None = None,
) -> list[dict[str, Any]]:
    perf = get_perf_logger()
    t0 = time.perf_counter()

    if query_embedding is None:
        t_embed = time.perf_counter()
        query_embedding = await asyncio.to_thread(embed_text, query_text)
        perf.info(
            "[nfd_chunk_search] chunk embedding in %.3fs",
            time.perf_counter() - t_embed,
        )

    tsvector = func.to_tsvector("english", NFDDocsChunks.content)
    tsquery = func.plainto_tsquery("english", query_text)
    base_conditions = []
    if start_date is not None:
        base_conditions.append(NFDDocsDocument.updated_at >= start_date)
    if end_date is not None:
        base_conditions.append(NFDDocsDocument.updated_at <= end_date)

    # Fetch extra chunks for better fusion (match KB pattern)
    n_results = top_k * 5

    semantic_search_cte = (
        select(
            NFDDocsChunks.id,
            NFDDocsChunks.document_id.label("document_id"),
            func.rank().over(order_by=NFDDocsChunks.embedding.op("<=>")(query_embedding)).label("rank"),
        )
        .join(NFDDocsDocument, NFDDocsChunks.document_id == NFDDocsDocument.id)
        .where(*base_conditions)
        .order_by(NFDDocsChunks.embedding.op("<=>")(query_embedding))
        .limit(n_results)
        .cte("nfd_chunk_semantic_search")
    )

    keyword_search_cte = (
        select(
            NFDDocsChunks.id,
            NFDDocsChunks.document_id.label("document_id"),
            func.rank().over(order_by=func.ts_rank_cd(tsvector, tsquery).desc()).label("rank"),
        )
        .join(NFDDocsDocument, NFDDocsChunks.document_id == NFDDocsDocument.id)
        .where(*base_conditions)
        .where(tsvector.op("@@")(tsquery))
        .order_by(func.ts_rank_cd(tsvector, tsquery).desc())
        .limit(n_results)
        .cte("nfd_chunk_keyword_search")
    )

    final_query = (
        select(
            NFDDocsChunks,
            (
                func.coalesce(1.0 / (_RRF_CONSTANT + semantic_search_cte.c.rank), 0.0)
                + func.coalesce(1.0 / (_RRF_CONSTANT + keyword_search_cte.c.rank), 0.0)
            ).label("score"),
        )
        .select_from(
            semantic_search_cte.outerjoin(
                keyword_search_cte,
                semantic_search_cte.c.id == keyword_search_cte.c.id,
                full=True,
            )
        )
        .join(
            NFDDocsChunks,
            NFDDocsChunks.id
            == func.coalesce(semantic_search_cte.c.id, keyword_search_cte.c.id),
        )
        .options(joinedload(NFDDocsChunks.document))
        .order_by(text("score DESC"))
        .limit(top_k)
    )

    result = await db_session.execute(final_query)
    chunk_rows = result.all()
    if not chunk_rows:
        return []

    chunk_results: list[dict[str, Any]] = []
    doc_scores: dict[int, float] = {}
    doc_order: list[int] = []

    for chunk, score in chunk_rows:
        document = chunk.document
        doc_id = document.id
        item = {
            "document_id": doc_id,
            "content": chunk.content,
            "score": float(score),
            "chunks": [{"chunk_id": f"doc-{chunk.id}", "content": chunk.content}],
            "document": _make_document_payload(doc_id, document.title, document.source),
            "source": "NFD_DOCS",
        }
        chunk_results.append(item)
        if doc_id not in doc_scores:
            doc_scores[doc_id] = float(score)
            doc_order.append(doc_id)
        else:
            doc_scores[doc_id] = max(doc_scores[doc_id], float(score))

    doc_ids = doc_order[:top_k]
    chunks_by_doc = await _fetch_chunks_for_documents(db_session, doc_ids)

    doc_map: dict[int, dict[str, Any]] = {
        doc_id: {
            "document_id": doc_id,
            "content": "",
            "score": float(doc_scores.get(doc_id, 0.0)),
            "chunks": [],
            "document": {},
            "source": "NFD_DOCS",
        }
        for doc_id in doc_ids
    }

    if doc_ids:
        doc_query = select(NFDDocsDocument).where(NFDDocsDocument.id.in_(doc_ids))
        doc_result = await db_session.execute(doc_query)
        docs = {doc.id: doc for doc in doc_result.scalars().all()}
    else:
        docs = {}

    for doc_id in doc_ids:
        doc = docs.get(doc_id)
        if doc is None:
            continue
        doc_map[doc_id]["document"] = _make_document_payload(doc.id, doc.title, doc.source)
        doc_map[doc_id]["chunks"] = chunks_by_doc.get(doc_id, [])
        doc_map[doc_id]["content"] = "\n\n".join(
            chunk["content"] for chunk in doc_map[doc_id]["chunks"] if chunk.get("content")
        )

    final_docs = [doc_map[doc_id] for doc_id in doc_ids if doc_id in doc_map]

    perf.info(
        "[nfd_chunk_search] chunk hybrid in %.3fs docs=%d",
        time.perf_counter() - t0,
        len(final_docs),
    )
    return final_docs


async def combined_nfd_docs_rrf_search(
    query_text: str,
    db_session: AsyncSession,
    top_k: int = 10,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    query_embedding: list[float] | None = None,
) -> list[dict[str, Any]]:
    perf = get_perf_logger()
    t0 = time.perf_counter()

    if query_embedding is None:
        t_embed = time.perf_counter()
        query_embedding = await asyncio.to_thread(embed_text, query_text)
        perf.info(
            "[nfd_search] shared embedding in %.3fs",
            time.perf_counter() - t_embed,
        )

    # Use separate sessions so the retrievers can run in parallel without
    # contending on a shared AsyncSession connection.
    async def _run_doc_search() -> list[dict[str, Any]]:
        async with async_session_maker() as session:
            return await _search_nfd_documents_hybrid(
                query_text=query_text,
                db_session=session,
                top_k=top_k,
                start_date=start_date,
                end_date=end_date,
                query_embedding=query_embedding,
            )

    async def _run_chunk_search() -> list[dict[str, Any]]:
        async with async_session_maker() as session:
            return await _search_nfd_chunks_hybrid(
                query_text=query_text,
                db_session=session,
                top_k=top_k,
                start_date=start_date,
                end_date=end_date,
                query_embedding=query_embedding,
            )

    t_parallel = time.perf_counter()
    doc_results, chunk_results = await asyncio.gather(
        _run_doc_search(),
        _run_chunk_search(),
    )
    perf.info(
        "[nfd_search] parallel hybrid retrievers in %.3fs doc_results=%d chunk_results=%d",
        time.perf_counter() - t_parallel,
        len(doc_results),
        len(chunk_results),
    )

    # Prefer chunk-level result data (so citations/chunk ids come from chunks)
    combined_results = _merge_rrf_results(
        chunk_results,
        doc_results,
        top_k=top_k,
    )

    perf.info(
        "[nfd_search] combined RRF in %.3fs doc_results=%d chunk_results=%d combined=%d",
        time.perf_counter() - t0,
        len(doc_results),
        len(chunk_results),
        len(combined_results),
    )
    return combined_results
