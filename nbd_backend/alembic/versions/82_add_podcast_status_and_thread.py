"""Add status and thread_id to podcasts

Revision ID: 82
Revises: 81
Create Date: 2026-01-27

Adds status enum and thread_id FK to podcasts.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "82"
down_revision: str | None = "81"
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
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE podcast_status AS ENUM ('pending', 'generating', 'ready', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    if not table_exists("podcasts"):
        return

    op.execute(
        """
        ALTER TABLE podcasts
        ADD COLUMN IF NOT EXISTS status podcast_status NOT NULL DEFAULT 'ready';
        """
    )

    op.execute(
        """
        ALTER TABLE podcasts
        ADD COLUMN IF NOT EXISTS thread_id INTEGER
        REFERENCES new_chat_threads(id) ON DELETE SET NULL;
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_podcasts_thread_id
        ON podcasts(thread_id);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_podcasts_status
        ON podcasts(status);
        """
    )


def downgrade() -> None:
    if table_exists("podcasts"):
        op.execute("DROP INDEX IF EXISTS ix_podcasts_status")
        op.execute("DROP INDEX IF EXISTS ix_podcasts_thread_id")
        op.execute("ALTER TABLE podcasts DROP COLUMN IF EXISTS thread_id")
        op.execute("ALTER TABLE podcasts DROP COLUMN IF EXISTS status")
    
    op.execute("DROP TYPE IF EXISTS podcast_status")
