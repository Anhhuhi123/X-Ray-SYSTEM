"""Drop user incentive tasks table

Revision ID: 110
Revises: 109
Create Date: 2026-04-21

This migration removes the incentive-task storage that backed the removed
Reddit / Discord / GitHub Star flow.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "110"
down_revision: str | None = "109"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TASK_ENUM_NAME = "incentivetasktype"
TABLE_NAME = "user_incentive_tasks"


def upgrade() -> None:
    """Drop the incentive task table and its enum type."""
    conn = op.get_bind()

    table_exists = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :table_name"
        ),
        {"table_name": TABLE_NAME},
    ).fetchone()

    if table_exists:
        op.drop_table(TABLE_NAME)

    enum_exists = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :type_name"),
        {"type_name": TASK_ENUM_NAME},
    ).fetchone()

    if enum_exists:
        postgresql.ENUM(name=TASK_ENUM_NAME).drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """Recreate the incentive task table and enum type."""
    conn = op.get_bind()

    enum_exists = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :type_name"),
        {"type_name": TASK_ENUM_NAME},
    ).fetchone()

    if not enum_exists:
        task_enum = postgresql.ENUM("GITHUB_STAR", name=TASK_ENUM_NAME, create_type=False)
        task_enum.create(op.get_bind(), checkfirst=True)

    table_exists = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :table_name"
        ),
        {"table_name": TABLE_NAME},
    ).fetchone()

    if not table_exists:
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "user_id",
                sa.UUID(as_uuid=True),
                sa.ForeignKey("user.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "task_type",
                postgresql.ENUM(
                    "GITHUB_STAR", name=TASK_ENUM_NAME, create_type=False
                ),
                nullable=False,
                index=True,
            ),
            sa.Column("pages_awarded", sa.Integer(), nullable=False),
            sa.Column(
                "completed_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
                index=True,
            ),
            sa.UniqueConstraint("user_id", "task_type", name="uq_user_incentive_task"),
        )
