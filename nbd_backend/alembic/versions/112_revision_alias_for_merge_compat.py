"""Compatibility alias revision for legacy stamp 112.

Revision ID: 112
Revises: 114
Create Date: 2026-04-26

Some environments were stamped with revision "112" while the merge migration
was corrected to revision "114". This no-op alias preserves upgrade paths for
those databases and keeps migration history resolvable.
"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "112"
down_revision: str | None = "114"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass