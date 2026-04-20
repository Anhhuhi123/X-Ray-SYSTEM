"""Cleanup decommissioned connector data (phase 1)

Revision ID: 107
Revises: 106
Create Date: 2026-04-13

Phase 1 migration for connector decommissioning:
- Removes documents with decommissioned document_type values.
- Removes search_source_connectors with decommissioned connector_type values.

This migration intentionally does NOT drop enum values yet.
Enum pruning should happen in a dedicated phase 2 migration after data cleanup
has been validated in all environments.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "107"
down_revision: str | None = "106"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DECOMMISSIONED_TYPES: tuple[str, ...] = (
    "SLACK_CONNECTOR",
    "TEAMS_CONNECTOR",
    "NOTION_CONNECTOR",
    "LINEAR_CONNECTOR",
    "JIRA_CONNECTOR",
    "CONFLUENCE_CONNECTOR",
    "CLICKUP_CONNECTOR",
    "GOOGLE_CALENDAR_CONNECTOR",
    "AIRTABLE_CONNECTOR",
    "GOOGLE_GMAIL_CONNECTOR",
    "DISCORD_CONNECTOR",
)


def _as_sql_in(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    enum_values_sql = _as_sql_in(DECOMMISSIONED_TYPES)

    # Remove documents first; this avoids dangling data and simplifies later enum pruning.
    op.execute(
        f"""
        DELETE FROM documents
        WHERE document_type::text IN ({enum_values_sql});
        """
    )

    # Remove decommissioned connectors from all spaces.
    op.execute(
        f"""
        DELETE FROM search_source_connectors
        WHERE connector_type::text IN ({enum_values_sql});
        """
    )


def downgrade() -> None:
    # Data cleanup is not safely reversible.
    pass
