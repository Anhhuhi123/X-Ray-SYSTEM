"""50_remove_podcast_chat_columns

Revision ID: 50
Revises: 49
Create Date: 2025-12-21

Removes chat_id and chat_state_version columns from podcasts table.
These columns were used for the old chat system podcast linking which
has been replaced by the new-chat content-based podcast generation.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "50"
down_revision: str | None = "49"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table_name)"
        ),
        {"table_name": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Upgrade schema - Remove chat_id and chat_state_version from podcasts."""
    if not table_exists("podcasts"):
        return

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("podcasts")]

    if "chat_id" in columns:
        op.drop_column("podcasts", "chat_id")

    if "chat_state_version" in columns:
        op.drop_column("podcasts", "chat_state_version")


def downgrade() -> None:
    """Downgrade schema - Re-add chat_id and chat_state_version to podcasts."""
    if not table_exists("podcasts"):
        return

    op.add_column(
        "podcasts",
        sa.Column("chat_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "podcasts",
        sa.Column("chat_state_version", sa.String(100), nullable=True),
    )
