"""Merge image removal and podcast/audio branches

Revision ID: 112
Revises: 111, 6353cf3787f1
Create Date: 2026-04-24
"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "112"
down_revision: str | tuple[str, str] | None = ("111", "6353cf3787f1")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass