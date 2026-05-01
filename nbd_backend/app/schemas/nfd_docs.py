"""
Schemas for NFD documentation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NFDDocsChunkRead(BaseModel):
    """Schema for a NFD docs chunk."""

    id: int
    content: str

    model_config = ConfigDict(from_attributes=True)


class NFDDocsDocumentRead(BaseModel):
    """Schema for a NFD docs document (without chunks)."""

    id: int
    title: str
    source: str
    content: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NFDDocsDocumentWithChunksRead(BaseModel):
    """Schema for a NFD docs document with its chunks."""

    id: int
    title: str
    source: str
    content: str
    chunks: list[NFDDocsChunkRead]

    model_config = ConfigDict(from_attributes=True)
