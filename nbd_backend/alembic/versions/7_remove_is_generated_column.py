"""Remove is_generated column from podcasts table

Revision ID: 7
Revises: 6

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7"
down_revision: str | None = "6"
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

    # Get the current database connection
    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if the column exists before attempting to drop it
    columns = [col["name"] for col in inspector.get_columns("podcasts")]
    if "is_generated" in columns:
        op.drop_column("podcasts", "is_generated")


def downgrade() -> None:
    if not table_exists("podcasts"):
        return

    # Add back the is_generated column with its original constraints
    op.add_column(
        "podcasts",
        sa.Column("is_generated", sa.Boolean(), nullable=False, server_default="false"),
    )
