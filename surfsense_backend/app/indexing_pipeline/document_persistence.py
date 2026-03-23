"""
document_persistence.py — Low-level DB helpers for the indexing pipeline.

Two public functions:
  - rollback_and_persist_failure: best-effort failure bookkeeping.
  - attach_sections_and_chunks: transactional section + chunk persistence
    (replaces the old flat attach_chunks_to_document).

The legacy ``attach_chunks_to_document`` is kept for any callers that have not
yet been migrated to the section-aware pipeline.
"""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.orm import object_session

from app.db import Chunk, Document, DocumentSection, DocumentStatus
from app.schemas.document_sections import ParsedSection


# ---------------------------------------------------------------------------
# Failure persistence helper
# ---------------------------------------------------------------------------

async def rollback_and_persist_failure(
    session: AsyncSession, document: Document, message: str
) -> None:
    """Roll back the current transaction and best-effort persist a failed status.

    Called exclusively from except blocks — must never raise, or the new
    exception would chain with the original and mask it entirely.
    """
    try:
        await session.rollback()
    except Exception:
        return  # Session is completely dead; nothing further we can do.
    try:
        await session.refresh(document)
        document.updated_at = datetime.now(UTC)
        document.status = DocumentStatus.failed(message)
        await session.commit()
    except Exception:
        pass  # Best-effort; document will be retried on the next sync.


# ---------------------------------------------------------------------------
# Legacy flat helper — kept for backward-compatible callers
# ---------------------------------------------------------------------------

def attach_chunks_to_document(document: Document, chunks: list) -> None:
    """Assign chunks to a document without triggering SQLAlchemy async lazy loading.

    .. deprecated::
        Prefer ``attach_sections_and_chunks`` for new code.  This function
        does *not* populate section-related fields.
    """
    set_committed_value(document, "chunks", chunks)
    session = object_session(document)
    if session is not None:
        if document.id is not None:
            for chunk in chunks:
                chunk.document_id = document.id
        session.add_all(chunks)


# ---------------------------------------------------------------------------
# New section-aware persistence helper
# ---------------------------------------------------------------------------

async def attach_sections_and_chunks(
    session: AsyncSession,
    document: Document,
    sections: list[ParsedSection],
    chunk_embedding_map: dict[str, list[float]],
) -> None:
    """
    Persist a list of ParsedSection objects (with their child ParsedChunk lists)
    into the database within the **caller's current transaction**.

    Strategy
    --------
    1. Delete all existing DocumentSection rows for this document.
       Chunks belonging to those sections are removed automatically via
       the ``CASCADE`` constraint that the migration defines via
       ``DocumentSection.chunks`` relationship.
    2. For each ParsedSection (already in depth-first, section_order order):
       a. Resolve ``parent_section_id`` from the ``temp_to_db`` map using
          the section's ``parent_temp_id``.
       b. INSERT the DocumentSection row and ``flush()`` to obtain its DB UUID.
       c. Record ``temp_id → DocumentSection`` in ``temp_to_db``.
       d. INSERT all child Chunk rows, linking them to the section.
    3. The caller is responsible for the final ``commit()``.

    Args:
        session:            The active async SQLAlchemy session.
        document:           The Document ORM object (must already have an id).
        sections:           Ordered flat list from ``parse_markdown_into_sections``.
        chunk_embedding_map: Maps chunk text → embedding vector.  Chunks whose
                             text is not in the map are stored without embeddings.
    """
    # Step 1 — delete old sections (CASCADE removes their chunks)
    await session.execute(
        delete(DocumentSection).where(DocumentSection.document_id == document.id)
    )
    await session.flush()

    # Step 2 — insert sections one by one to resolve parent UUIDs in-flight
    # temp_id (UUID generated during parsing) → flushed DocumentSection object
    temp_to_db: dict[UUID, DocumentSection] = {}

    chunks_to_add: list[Chunk] = []

    for parsed_section in sections:
        # Resolve parent: look up the DB object for the parent's temp UUID
        parent_db_section: DocumentSection | None = None
        if parsed_section.parent_temp_id is not None:
            parent_db_section = temp_to_db.get(parsed_section.parent_temp_id)

        db_section = DocumentSection(
            document_id=document.id,
            heading_text=parsed_section.heading_text,
            normalized_heading=parsed_section.heading_text.lower().strip(),
            heading_level=parsed_section.heading_level,
            # SQLAlchemy resolves the FK from the related object automatically
            parent_section_id=parent_db_section.id if parent_db_section else None,
            section_order=parsed_section.section_order,
            raw_markdown=parsed_section.raw_markdown,
            plain_text=parsed_section.plain_text,
            section_type=parsed_section.section_type,
            section_metadata=parsed_section.metadata,
        )
        session.add(db_section)
        # Flush to get the server-assigned UUID before processing child objects
        await session.flush()

        # Record the mapping so children can reference this section
        temp_to_db[parsed_section.temp_id] = db_section

        # Build Chunk rows for this section
        for parsed_chunk in parsed_section.chunks:
            embedding = chunk_embedding_map.get(parsed_chunk.content)
            db_chunk = Chunk(
                content=parsed_chunk.content,
                embedding=embedding,
                document_id=document.id,
                section_id=db_section.id,
                chunk_order_in_section=parsed_chunk.chunk_order_in_section,
                heading_text=parsed_section.heading_text,
                heading_level=parsed_section.heading_level,
                section_type=parsed_section.section_type,
                chunk_type=parsed_chunk.chunk_type,
                content_hash=parsed_chunk.content_hash,
                chunk_metadata={},
            )
            chunks_to_add.append(db_chunk)

    # Bulk-add all chunks in one shot
    session.add_all(chunks_to_add)
    # The caller commits the transaction (document + sections + chunks together)
