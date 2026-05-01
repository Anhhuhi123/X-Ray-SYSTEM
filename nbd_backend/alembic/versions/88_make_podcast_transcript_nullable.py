"""Make podcast_transcript nullable

Revision ID: 88
Revises: 87
Create Date: 2026-02-02

The podcast workflow now creates a podcast record with PENDING status first,
then fills in the transcript after generation completes. This requires
podcast_transcript to be nullable.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "88"
down_revision: str | None = "87"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


import sqlalchemy as sa


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
    if not table_exists("podcasts"):
        return

    # Make podcast_transcript nullable and remove the server default
    op.execute(
        """
        ALTER TABLE podcasts
        ALTER COLUMN podcast_transcript DROP NOT NULL;
        """
    )
    op.execute(
        """
        ALTER TABLE podcasts
        ALTER COLUMN podcast_transcript DROP DEFAULT;
        """
    )


def downgrade() -> None:
    if not table_exists("podcasts"):
        return

    # Set empty JSON for any NULL values before adding NOT NULL constraint
    op.execute(
        """
        UPDATE podcasts
        SET podcast_transcript = '{}'::jsonb
        WHERE podcast_transcript IS NULL;
        """
    )
    op.execute(
        """
        ALTER TABLE podcasts
        ALTER COLUMN podcast_transcript SET DEFAULT '{}';
        """
    )
    op.execute(
        """
        ALTER TABLE podcasts
        ALTER COLUMN podcast_transcript SET NOT NULL;
        """
    )
