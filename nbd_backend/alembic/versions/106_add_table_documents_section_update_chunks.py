"""add document_sections and enhance chunks

Revision ID: 106
Revises: 105
Create Date: 2026-03-23 09:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "106"
down_revision: str | None = "105"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DOCUMENT_SECTIONS_TABLE = "document_sections"
CHUNKS_TABLE = "chunks"


def _table_exists(bind: sa.engine.Connection, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _column_exists(
    bind: sa.engine.Connection, table_name: str, column_name: str
) -> bool:
    return any(
        column["name"] == column_name
        for column in sa.inspect(bind).get_columns(table_name)
    )


def _index_exists(bind: sa.engine.Connection, table_name: str, index_name: str) -> bool:
    return any(
        index["name"] == index_name
        for index in sa.inspect(bind).get_indexes(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, DOCUMENT_SECTIONS_TABLE):
        op.create_table(
            DOCUMENT_SECTIONS_TABLE,
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

    for index_name, columns in (
        ("ix_document_sections_document_id", ["document_id"]),
        ("ix_document_sections_parent_section_id", ["parent_section_id"]),
        (
            "ix_document_sections_document_id_section_order",
            ["document_id", "section_order"],
        ),
        ("ix_document_sections_section_type", ["section_type"]),
    ):
        if not _index_exists(bind, DOCUMENT_SECTIONS_TABLE, index_name):
            op.create_index(index_name, DOCUMENT_SECTIONS_TABLE, columns, unique=False)

    if _table_exists(bind, CHUNKS_TABLE):
        if not _column_exists(bind, CHUNKS_TABLE, "section_id"):
            op.add_column(
                CHUNKS_TABLE,
                sa.Column(
                    "section_id",
                    postgresql.UUID(as_uuid=True),
                    sa.ForeignKey("document_sections.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )
        if not _column_exists(bind, CHUNKS_TABLE, "chunk_order_in_section"):
            op.add_column(
                CHUNKS_TABLE,
                sa.Column("chunk_order_in_section", sa.Integer(), nullable=True),
            )
        if not _column_exists(bind, CHUNKS_TABLE, "heading_text"):
            op.add_column(
                CHUNKS_TABLE, sa.Column("heading_text", sa.Text(), nullable=True)
            )
        if not _column_exists(bind, CHUNKS_TABLE, "heading_level"):
            op.add_column(
                CHUNKS_TABLE, sa.Column("heading_level", sa.Integer(), nullable=True)
            )
        if not _column_exists(bind, CHUNKS_TABLE, "section_type"):
            op.add_column(
                CHUNKS_TABLE, sa.Column("section_type", sa.Text(), nullable=True)
            )
        if not _column_exists(bind, CHUNKS_TABLE, "chunk_type"):
            op.add_column(
                CHUNKS_TABLE, sa.Column("chunk_type", sa.Text(), nullable=True)
            )
        if not _column_exists(bind, CHUNKS_TABLE, "content_hash"):
            op.add_column(
                CHUNKS_TABLE, sa.Column("content_hash", sa.Text(), nullable=True)
            )
        if not _column_exists(bind, CHUNKS_TABLE, "metadata"):
            op.add_column(
                CHUNKS_TABLE,
                sa.Column(
                    "metadata",
                    postgresql.JSONB(astext_type=sa.Text()),
                    nullable=False,
                    server_default=sa.text("'{}'::jsonb"),
                ),
            )
        if not _column_exists(bind, CHUNKS_TABLE, "updated_at"):
            op.add_column(
                CHUNKS_TABLE,
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.text("NOW()"),
                ),
            )

        for index_name, columns in (
            ("ix_chunks_section_id", ["section_id"]),
            (
                "ix_chunks_document_id_section_id_chunk_order",
                ["document_id", "section_id", "chunk_order_in_section"],
            ),
            ("ix_chunks_section_type", ["section_type"]),
            ("ix_chunks_chunk_type", ["chunk_type"]),
            ("ix_chunks_content_hash", ["content_hash"]),
        ):
            if not _index_exists(bind, CHUNKS_TABLE, index_name):
                op.create_index(index_name, CHUNKS_TABLE, columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    for index_name in (
        "ix_chunks_content_hash",
        "ix_chunks_chunk_type",
        "ix_chunks_section_type",
        "ix_chunks_document_id_section_id_chunk_order",
        "ix_chunks_section_id",
    ):
        if _index_exists(bind, CHUNKS_TABLE, index_name):
            op.drop_index(index_name, table_name=CHUNKS_TABLE)

    for column_name in (
        "updated_at",
        "metadata",
        "content_hash",
        "chunk_type",
        "section_type",
        "heading_level",
        "heading_text",
        "chunk_order_in_section",
        "section_id",
    ):
        if _column_exists(bind, CHUNKS_TABLE, column_name):
            op.drop_column(CHUNKS_TABLE, column_name)

    for index_name in (
        "ix_document_sections_section_type",
        "ix_document_sections_document_id_section_order",
        "ix_document_sections_parent_section_id",
        "ix_document_sections_document_id",
    ):
        if _index_exists(bind, DOCUMENT_SECTIONS_TABLE, index_name):
            op.drop_index(index_name, table_name=DOCUMENT_SECTIONS_TABLE)

    if _table_exists(bind, DOCUMENT_SECTIONS_TABLE):
        op.drop_table(DOCUMENT_SECTIONS_TABLE)
