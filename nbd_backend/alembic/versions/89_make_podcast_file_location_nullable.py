"""Make podcast file_location nullable

Revision ID: 89
Revises: 88
Create Date: 2026-02-03

The podcast workflow creates a podcast record with PENDING status first,
then fills in the file_location after audio generation completes. This requires
file_location to be nullable.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "89"
down_revision: str | None = "88"
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
    if not table_exists("podcasts"):
        return

    # Make file_location nullable
    op.execute(
        """
        ALTER TABLE podcasts
        ALTER COLUMN file_location DROP NOT NULL;
        """
    )


def downgrade() -> None:
    if not table_exists("podcasts"):
        return

    # Set empty string for any NULL values before adding NOT NULL constraint
    op.execute(
        """
        UPDATE podcasts
        SET file_location = ''
        WHERE file_location IS NULL;
        """
    )
    op.execute(
        """
        ALTER TABLE podcasts
        ALTER COLUMN file_location SET NOT NULL;
        """
    )
