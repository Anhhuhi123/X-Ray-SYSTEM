"""
Pydantic schemas for DocumentSection and related DTOs.

ParsedSection / ParsedChunk are internal-only DTOs used by the indexing
pipeline to carry structured parsing results between the chunker and the
persistence layer.  They are never serialised to the API directly.

DocumentSectionRead is the external-facing response schema.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Internal pipeline DTOs
# ---------------------------------------------------------------------------


class ParsedChunk(BaseModel):
    """A single text chunk extracted from a ParsedSection."""

    content: str
    chunk_order_in_section: int
    chunk_type: str = "text"
    content_hash: str | None = None
    # Embedding is attached after embed_texts() and stored separately
    embedding: list[float] | None = None


class ParsedSection(BaseModel):
    """
    Represents one heading-delimited section parsed from a Markdown document.

    ``temp_id`` is a transient UUID generated at parse time.  It is used by
    the persistence layer to resolve parent_section_id references before the
    rows are flushed to the database.  It must NOT be confused with the final
    DB UUID.
    """

    # Internal identifier — generated on construction, not persisted as-is.
    temp_id: UUID = Field(default_factory=uuid4, exclude=True)

    heading_text: str
    heading_level: int  # 1-6 matching the number of '#' chars
    raw_markdown: str  # Full markdown text of the section (heading + body)
    plain_text: str  # Body text with markup stripped
    section_order: int  # 0-based index in the flat list of sections
    # Points to the temp_id of the parent ParsedSection (None = root section)
    parent_temp_id: UUID | None = None
    section_type: str | None = None  # e.g. "title", "chapter", "section"
    metadata: dict = Field(default_factory=dict)
    chunks: list[ParsedChunk] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------
# API response schema
# ---------------------------------------------------------------------------


class DocumentSectionRead(BaseModel):
    """External-facing representation of a DocumentSection row."""

    id: UUID
    document_id: int
    heading_text: str
    normalized_heading: str | None = None
    heading_level: int
    parent_section_id: UUID | None = None
    section_order: int
    raw_markdown: str | None = None
    plain_text: str | None = None
    section_type: str | None = None
    section_confidence: float | None = None

    model_config = ConfigDict(from_attributes=True)
