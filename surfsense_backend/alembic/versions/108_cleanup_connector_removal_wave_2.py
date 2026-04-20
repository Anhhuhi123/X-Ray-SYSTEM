"""Cleanup removed connector data (wave 2)

Revision ID: 108
Revises: 107
Create Date: 2026-04-14

This migration hard-deletes data for connector families removed from runtime:
- Google Drive connector
- Luma connector
- Circleback connector
- Composio connectors (Drive/Gmail/Calendar)
- YouTube document artifacts

Enum values are intentionally kept for compatibility with existing DB enum types.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "108"
down_revision: str | None = "107"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


REMOVED_CONNECTOR_TYPES: tuple[str, ...] = (
    "GOOGLE_DRIVE_CONNECTOR",
    "LUMA_CONNECTOR",
    "CIRCLEBACK_CONNECTOR",
    "COMPOSIO_GMAIL_CONNECTOR",
    "COMPOSIO_GOOGLE_CALENDAR_CONNECTOR",
)

REMOVED_DOCUMENT_TYPES: tuple[str, ...] = (
    "GOOGLE_DRIVE_FILE",
    "LUMA_CONNECTOR",
    "CIRCLEBACK",
    "YOUTUBE_VIDEO",
    "COMPOSIO_GMAIL_CONNECTOR",
    "COMPOSIO_GOOGLE_CALENDAR_CONNECTOR",
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
