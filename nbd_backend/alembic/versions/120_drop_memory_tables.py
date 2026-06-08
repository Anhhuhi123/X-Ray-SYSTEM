"""Drop user_memories and shared_memories tables and memorycategory enum.

Revision ID: 120
Revises: 119

Changes:
1. Drop shared_memories table (created in migration 96)
2. Drop user_memories table (created in migration 73)
3. Drop memorycategory PostgreSQL enum type
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "120"
down_revision: str | None = "119"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "shared_memories" in existing_tables:
        op.drop_index("ix_shared_memories_updated_at", table_name="shared_memories", if_exists=True)
        op.drop_index("ix_shared_memories_search_space_id", table_name="shared_memories", if_exists=True)
        op.drop_index("ix_shared_memories_created_by_id", table_name="shared_memories", if_exists=True)
        op.drop_table("shared_memories")

    if "user_memories" in existing_tables:
        op.drop_index("ix_user_memories_updated_at", table_name="user_memories", if_exists=True)
        op.drop_index("ix_user_memories_search_space_id", table_name="user_memories", if_exists=True)
        op.drop_index("ix_user_memories_user_id", table_name="user_memories", if_exists=True)
        op.drop_index("ix_user_memories_category", table_name="user_memories", if_exists=True)
        op.drop_index("ix_user_memories_user_search_space", table_name="user_memories", if_exists=True)
        op.drop_table("user_memories")

    # Drop the memorycategory enum type if it exists
    conn.execute(sa.text("DROP TYPE IF EXISTS memorycategory CASCADE"))


def downgrade() -> None:
    # Recreate memorycategory enum
    conn = op.get_bind()
    conn.execute(sa.text(
        "CREATE TYPE memorycategory AS ENUM ('preference', 'fact', 'instruction', 'context')"
    ))

    # Recreate user_memories table
    op.create_table(
        "user_memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, index=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("search_space_id", sa.Integer(), nullable=True, index=True),
        sa.Column("memory_text", sa.Text(), nullable=False),
        sa.Column("category", sa.Enum("preference", "fact", "instruction", "context", name="memorycategory"), nullable=False, server_default="fact"),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["search_space_id"], ["searchspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Recreate shared_memories table
    op.create_table(
        "shared_memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, index=True),
        sa.Column("search_space_id", sa.Integer(), nullable=False, index=True),
        sa.Column("created_by_id", sa.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("memory_text", sa.Text(), nullable=False),
        sa.Column("category", sa.Enum("preference", "fact", "instruction", "context", name="memorycategory"), nullable=False, server_default="fact"),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["search_space_id"], ["searchspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
