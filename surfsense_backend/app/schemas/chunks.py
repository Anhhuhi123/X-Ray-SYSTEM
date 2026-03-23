from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .base import IDModel, TimestampModel


class ChunkBase(BaseModel):
    content: str
    document_id: int


class ChunkCreate(ChunkBase):
    pass


class ChunkUpdate(ChunkBase):
    pass


class ChunkRead(ChunkBase, IDModel, TimestampModel):
    # New section-aware fields (migration 106)
    section_id: UUID | None = None
    chunk_order_in_section: int | None = None
    heading_text: str | None = None
    heading_level: int | None = None
    section_type: str | None = None
    chunk_type: str | None = None
    content_hash: str | None = None

    model_config = ConfigDict(from_attributes=True)
