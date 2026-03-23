"""add document_sections and enhance chunks

Revision ID: add_document_sections_and_enhance_chunks
Revises: <PUT_PREVIOUS_REVISION_ID_HERE>
Create Date: 2026-03-23 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from collections.abc import Sequence



# revision identifiers, used by Alembic.
revision: str = "106"
down_revision: str | None = "105"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ============================================================
    # 1) Create document_sections table
    # ============================================================
    op.create_table(
        "document_sections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("heading_text", sa.Text(), nullable=False),
        sa.Column("normalized_heading", sa.Text(), nullable=True),
        sa.Column("heading_level", sa.Integer(), nullable=False),
        sa.Column(
            "parent_section_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_sections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("section_order", sa.Integer(), nullable=False),
        sa.Column("raw_markdown", sa.Text(), nullable=True),
        sa.Column("plain_text", sa.Text(), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("section_type", sa.Text(), nullable=True),
        sa.Column("section_confidence", sa.Float(), nullable=True),
        sa.Column("classification_source", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Indexes for document_sections
    op.create_index(
        "ix_document_sections_document_id",
        "document_sections",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_sections_parent_section_id",
        "document_sections",
        ["parent_section_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_sections_document_id_section_order",
        "document_sections",
        ["document_id", "section_order"],
        unique=False,
    )
    op.create_index(
        "ix_document_sections_section_type",
        "document_sections",
        ["section_type"],
        unique=False,
    )

    # ============================================================
    # 2) Alter chunks table
    # ============================================================
    op.add_column(
        "chunks",
        sa.Column(
            "section_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_sections.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "chunks",
        sa.Column("chunk_order_in_section", sa.Integer(), nullable=True),
    )
    op.add_column(
        "chunks",
        sa.Column("heading_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "chunks",
        sa.Column("heading_level", sa.Integer(), nullable=True),
    )
    op.add_column(
        "chunks",
        sa.Column("section_type", sa.Text(), nullable=True),
    )
    op.add_column(
        "chunks",
        sa.Column("chunk_type", sa.Text(), nullable=True),
    )
    op.add_column(
        "chunks",
        sa.Column("content_hash", sa.Text(), nullable=True),
    )
    op.add_column(
        "chunks",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "chunks",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Indexes for chunks
    op.create_index(
        "ix_chunks_section_id",
        "chunks",
        ["section_id"],
        unique=False,
    )
    op.create_index(
        "ix_chunks_document_id_section_id_chunk_order",
        "chunks",
        ["document_id", "section_id", "chunk_order_in_section"],
        unique=False,
    )
    op.create_index(
        "ix_chunks_section_type",
        "chunks",
        ["section_type"],
        unique=False,
    )
    op.create_index(
        "ix_chunks_chunk_type",
        "chunks",
        ["chunk_type"],
        unique=False,
    )
    op.create_index(
        "ix_chunks_content_hash",
        "chunks",
        ["content_hash"],
        unique=False,
    )


def downgrade() -> None:
    # ============================================================
    # 1) Drop indexes on chunks
    # ============================================================
    op.drop_index("ix_chunks_content_hash", table_name="chunks")
    op.drop_index("ix_chunks_chunk_type", table_name="chunks")
    op.drop_index("ix_chunks_section_type", table_name="chunks")
    op.drop_index("ix_chunks_document_id_section_id_chunk_order", table_name="chunks")
    op.drop_index("ix_chunks_section_id", table_name="chunks")

    # ============================================================
    # 2) Drop columns from chunks
    # ============================================================
    op.drop_column("chunks", "updated_at")
    op.drop_column("chunks", "metadata")
    op.drop_column("chunks", "content_hash")
    op.drop_column("chunks", "chunk_type")
    op.drop_column("chunks", "section_type")
    op.drop_column("chunks", "heading_level")
    op.drop_column("chunks", "heading_text")
    op.drop_column("chunks", "chunk_order_in_section")
    op.drop_column("chunks", "section_id")

    # ============================================================
    # 3) Drop indexes on document_sections
    # ============================================================
    op.drop_index("ix_document_sections_section_type", table_name="document_sections")
    op.drop_index(
        "ix_document_sections_document_id_section_order",
        table_name="document_sections",
    )
    op.drop_index(
        "ix_document_sections_parent_section_id",
        table_name="document_sections",
    )
    op.drop_index(
        "ix_document_sections_document_id",
        table_name="document_sections",
    )

    # ============================================================
    # 4) Drop document_sections table
    # ============================================================
    op.drop_table("document_sections")