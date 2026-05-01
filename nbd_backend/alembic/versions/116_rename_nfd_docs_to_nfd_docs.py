"""Rename nfd_docs tables to nfd_docs

Revision ID: 116
Revises: 115
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "116"
down_revision: str | None = "115"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename nfd_docs_documents and nfd_docs_chunks tables to nfd_docs_*"""
    pass


def downgrade() -> None:
    """Rename nfd_docs_* tables back to nfd_docs_*"""
    pass
