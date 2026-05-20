"""
Routes for NFD documentation.

These endpoints support the citation system for NFD docs,
allowing the frontend to fetch document details when a user clicks
on a [citation:doc-XXX] link.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import (
    NFDDocsChunks,
    NFDDocsDocument,
    User,
    get_async_session,
)
from app.schemas import PaginatedResponse
from app.schemas.nfd_docs import (
    NFDDocsChunkRead,
    NFDDocsDocumentRead,
    NFDDocsDocumentWithChunksRead,
)
from app.users import current_active_user

router = APIRouter()


@router.get(
    "/nfd-docs/by-chunk/{chunk_id}",
    response_model=NFDDocsDocumentWithChunksRead,
)
async def get_nfd_doc_by_chunk_id(
    chunk_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """
    Retrieves a NFD documentation document based on a chunk ID.

    This endpoint is used by the frontend to resolve [citation:doc-XXX] links.
    """
    try:
        # Get the chunk
        chunk_result = await session.execute(
            select(NFDDocsChunks).filter(NFDDocsChunks.id == chunk_id)
        )
        chunk = chunk_result.scalars().first()

        if not chunk:
            raise HTTPException(
                status_code=404,
                detail=f"NFD docs chunk with id {chunk_id} not found",
            )

        # Get the associated document with all its chunks
        document_result = await session.execute(
            select(NFDDocsDocument)
            .options(selectinload(NFDDocsDocument.chunks))
            .filter(NFDDocsDocument.id == chunk.document_id)
        )
        document = document_result.scalars().first()

        if not document:
            raise HTTPException(
                status_code=404,
                detail="NFD docs document not found",
            )

        # Sort chunks by ID
        sorted_chunks = sorted(document.chunks, key=lambda x: x.id)

        return NFDDocsDocumentWithChunksRead(
            id=document.id,
            title=document.title,
            source=document.source,
            content=document.content,
            chunks=[
                NFDDocsChunkRead(id=c.id, content=c.content) for c in sorted_chunks
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve NFD documentation: {e!s}",
        ) from e


@router.get(
    "/nfd-docs",
    response_model=PaginatedResponse[NFDDocsDocumentRead],
)
async def list_nfd_docs(
    page: int = 0,
    page_size: int = 50,
    title: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    """
    List all NFD documentation documents.

    Args:
        page: Zero-based page index.
        page_size: Number of items per page (default: 50).
        title: Optional title filter (case-insensitive substring match).
        session: Database session (injected).
        user: Current authenticated user (injected).

    Returns:
        PaginatedResponse[NFDDocsDocumentRead]: Paginated list of NFD docs.
    """
    try:
        # Base query
        query = select(NFDDocsDocument)
        count_query = select(func.count()).select_from(NFDDocsDocument)

        # Filter by title if provided
        if title and title.strip():
            query = query.filter(NFDDocsDocument.title.ilike(f"%{title}%"))
            count_query = count_query.filter(NFDDocsDocument.title.ilike(f"%{title}%"))

        # Get total count
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Calculate offset
        offset = page * page_size

        # Get paginated results
        result = await session.execute(
            query.order_by(NFDDocsDocument.title).offset(offset).limit(page_size)
        )
        docs = result.scalars().all()

        # Convert to response format
        items = [
            NFDDocsDocumentRead(
                id=doc.id,
                title=doc.title,
                source=doc.source,
                content=doc.content,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in docs
        ]

        has_more = (offset + len(items)) < total

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list NFD documentation: {e!s}",
        ) from e
