"""
NFD documentation search tool with enhanced features.

This tool allows the agent to search the pre-indexed NFD documentation
to help users with questions about how to use the application.

Features:
- Vector similarity search on documentation
- Degenerate query handling (*, **, empty) → recency browse fallback
- Deduplication by document_id + content_hash
- Context budget management based on model context window
- Optional date range filtering
- Performance logging

The documentation is indexed at deployment time from MDX files and stored
in dedicated tables (nfd_docs_documents, nfd_docs_chunks).
"""

import asyncio
import time
from datetime import datetime
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.agents.new_chat.tools.document_search_base import (
    _BROWSE_MAX_CHUNKS_PER_DOC,
    _compute_tool_output_budget,
    _is_degenerate_query,
    format_documents_for_context,
)
from app.db import NFDDocsDocument, shielded_async_session
from app.retriever.nfd_docs_hybrid_search import combined_nfd_docs_rrf_search
from app.utils.document_converters import embed_text
from app.utils.perf import get_perf_logger


async def _browse_recent_nfd_docs(
    top_k: int,
    start_date: datetime | None,
    end_date: datetime | None,
) -> list[dict[str, Any]]:
    """Return the most-recent NFD documentation (recency-ordered, no search ranking).

    Used as a fallback when the search query is degenerate (e.g. ``*``) and
    semantic search would produce arbitrary results.  Returns document-grouped
    dicts in the same shape as the regular search so the rest of the pipeline works.
    """
    perf = get_perf_logger()
    t0 = time.perf_counter()

    base_conditions = []

    if start_date is not None:
        base_conditions.append(NFDDocsDocument.updated_at >= start_date)
    if end_date is not None:
        base_conditions.append(NFDDocsDocument.updated_at <= end_date)

    async with shielded_async_session() as session:
        doc_query = (
            select(NFDDocsDocument)
            .options(joinedload(NFDDocsDocument.chunks))
            .where(*base_conditions)
            .order_by(NFDDocsDocument.updated_at.desc())
            .limit(top_k)
        )
        result = await session.execute(doc_query)
        documents = result.scalars().unique().all()

        if not documents:
            return []

    # Transform to document-grouped format
    results: list[dict[str, Any]] = []
    for doc in documents:
        chunks_list = []
        for chunk in doc.chunks[:_BROWSE_MAX_CHUNKS_PER_DOC]:
            chunks_list.append(
                {"chunk_id": f"doc-{chunk.id}", "content": chunk.content}
            )

        results.append(
            {
                "document": {
                    "id": f"doc-{doc.id}",
                    "title": doc.title,
                    "document_type": "NFD_DOCS",
                    "metadata": {"source": doc.source},
                },
                "chunks": chunks_list,
                "source": "NFD_DOCS",
            }
        )

    perf.info(
        "[nfd_browse] recency browse in %.3fs docs=%d",
        time.perf_counter() - t0,
        len(results),
    )
    return results


async def search_nfd_docs_async(
    query: str,
    db_session: AsyncSession,
    top_k: int = 10,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    max_input_tokens: int | None = None,
) -> str:
    """
    Search NFD documentation using vector similarity (or recency fallback).

    Args:
        query: The search query about NFD usage
        db_session: Database session for executing queries
        top_k: Number of results to return
        start_date: Optional start datetime for filtering documents
        end_date: Optional end datetime for filtering documents
        max_input_tokens: Model context window (tokens) for budget management

    Returns:
        Formatted string with relevant documentation content
    """
    perf = get_perf_logger()
    t0 = time.perf_counter()

    all_documents: list[dict[str, Any]] = []

    # --- Fast-path: degenerate queries (*, **, empty, etc.) ---
    if _is_degenerate_query(query):
        perf.info(
            "[nfd_search] degenerate query %r detected - falling back to recency browse",
            query,
        )
        browse_results = await _browse_recent_nfd_docs(
            top_k=top_k,
            start_date=start_date,
            end_date=end_date,
        )
        all_documents.extend(browse_results)

        output_budget = _compute_tool_output_budget(max_input_tokens)
        result = format_documents_for_context(
            all_documents,
            max_chars=output_budget,
            max_chunks_per_doc=_BROWSE_MAX_CHUNKS_PER_DOC,
        )
        perf.info(
            "[nfd_search] TOTAL (browse) in %.3fs total_docs=%d output_chars=%d budget=%d",
            time.perf_counter() - t0,
            len(all_documents),
            len(result),
            output_budget,
        )
        return result

    # --- Normal path: hybrid retrieval + RRF fusion ---
    t_embed = time.perf_counter()
    query_embedding = await asyncio.to_thread(embed_text, query)
    perf.info(
        "[nfd_search] embedding computed in %.3fs",
        time.perf_counter() - t_embed,
    )

    hybrid_results = await combined_nfd_docs_rrf_search(
        query_text=query,
        db_session=db_session,
        top_k=top_k,
        start_date=start_date,
        end_date=end_date,
        query_embedding=query_embedding,
    )

    # Format with context budget management
    output_budget = _compute_tool_output_budget(max_input_tokens)
    formatted_result = format_documents_for_context(
        hybrid_results,
        max_chars=output_budget,
    )

    perf.info(
        "[nfd_search] TOTAL in %.3fs total_docs=%d output_chars=%d budget=%d max_input_tokens=%s",
        time.perf_counter() - t0,
        len(hybrid_results),
        len(formatted_result),
        output_budget,
        max_input_tokens,
    )
    return formatted_result


class SearchNFDDocsInput(BaseModel):
    """Input schema for the search_nfd_docs tool."""

    query: str = Field(
        description=(
            "The search query about NFD - use specific natural language terms. "
            "NEVER use wildcards like '*'; instead describe what you want "
            "(e.g. 'how to use browser extension' or 'configure obsidian connector')."
        ),
    )
    top_k: int = Field(
        default=10,
        description="Number of results to retrieve (default: 10). Keep ≤20 for focused searches.",
    )
    start_date: str | None = Field(
        default=None,
        description="Optional ISO date/datetime for filtering documentation (e.g. '2025-01-01')",
    )
    end_date: str | None = Field(
        default=None,
        description="Optional ISO date/datetime for filtering documentation (e.g. '2025-01-31')",
    )


def create_search_nfd_docs_tool(
    db_session: AsyncSession,
    max_input_tokens: int | None = None,
) -> StructuredTool:
    """
    Factory function to create the search_nfd_docs tool.

    Args:
        db_session: Database session for executing queries
        max_input_tokens: Model context window (tokens) from litellm model info

    Returns:
        A configured StructuredTool instance for searching NFD documentation
    """
    _max_input_tokens = max_input_tokens

    async def _search_nfd_docs_impl(
        query: str,
        top_k: int = 10,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> str:
        """Implementation function for NFD docs search."""
        from app.agents.new_chat.utils import parse_date_or_datetime

        parsed_start: datetime | None = None
        parsed_end: datetime | None = None

        if start_date:
            parsed_start = parse_date_or_datetime(start_date)
        if end_date:
            parsed_end = parse_date_or_datetime(end_date)

        return await search_nfd_docs_async(
            query=query,
            db_session=db_session,
            top_k=top_k,
            start_date=parsed_start,
            end_date=parsed_end,
            max_input_tokens=_max_input_tokens,
        )

    dynamic_description = """Search NFD system documentation for help using the application.

Use this tool when users ask questions about:
- How to use NFD features and functionality
- Installation and setup instructions
- Configuration options and settings
- Troubleshooting common issues
- Available connectors and integrations
- Browser extension usage and setup
- API documentation and endpoints
- Account management and authentication

This searches the official NFD documentation indexed at deployment time.
It does NOT search the user's personal knowledge base - use search_knowledge_base for that.

IMPORTANT:
- Use specific, descriptive natural language queries (e.g., "how to setup obsidian connector")
- Avoid wildcards like '*' or single characters - they yield poor results
- Prefer multiple focused searches over one broad search with high top_k"""

    tool = StructuredTool(
        name="search_nfd_docs",
        description=dynamic_description,
        coroutine=_search_nfd_docs_impl,
        args_schema=SearchNFDDocsInput,
    )

    return tool
