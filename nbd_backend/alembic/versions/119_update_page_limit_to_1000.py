"""Update page limit from 500 to 1000 for all users

Revision ID: 119
Revises: 118

Changes:
1. Update pages_limit from 500 to 1000 for all users who still have the old default (500)
"""

from collections.abc import Sequence

from alembic import op

revision: str = "119"
down_revision: str | None = "118"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE \"user\" SET pages_limit = 1000 WHERE pages_limit = 500")


def downgrade() -> None:
    op.execute("UPDATE \"user\" SET pages_limit = 500 WHERE pages_limit = 1000")
