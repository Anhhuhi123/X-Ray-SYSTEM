"""Cleanup removed connector data (wave 3)

Revision ID: 109
Revises: 108
Create Date: 2026-04-14

This migration hard-deletes data for connector families removed from runtime:
- GitHub connector
- Elasticsearch connector
- BookStack connector
- Luma connector (final cleanup)

Enum values are intentionally kept in PostgreSQL for migration compatibility.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "109"
down_revision: str | None = "108"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


REMOVED_CONNECTOR_TYPES: tuple[str, ...] = (
    "GITHUB_CONNECTOR",
    "ELASTICSEARCH_CONNECTOR",
    "BOOKSTACK_CONNECTOR",
    "LUMA_CONNECTOR",
)

REMOVED_DOCUMENT_TYPES: tuple[str, ...] = (
    "GITHUB_CONNECTOR",
    "ELASTICSEARCH_CONNECTOR",
    "BOOKSTACK_CONNECTOR",
    "LUMA_CONNECTOR",
)


def _as_sql_in(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    connector_values_sql = _as_sql_in(REMOVED_CONNECTOR_TYPES)
    document_values_sql = _as_sql_in(REMOVED_DOCUMENT_TYPES)

    # Remove documents first so dependent data is cleared before connector rows.
    op.execute(
        f"""
        DELETE FROM documents
        WHERE document_type::text IN ({document_values_sql});
        """
    )

    op.execute(
        f"""
        DELETE FROM search_source_connectors
        WHERE connector_type::text IN ({connector_values_sql});
        """
    )


def downgrade() -> None:
    # Hard-delete migration; cannot safely restore removed data.
    pass
