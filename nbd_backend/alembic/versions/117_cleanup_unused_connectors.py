"""Cleanup unused connectors from enums.

Revision ID: 117
Revises: 116
Create Date: 2026-05-08

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "117"
down_revision: str | None = "116"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


REMOVED_VALUES: tuple[str, ...] = (
    "SLACK_CONNECTOR",
    "TEAMS_CONNECTOR",
    "DISCORD_CONNECTOR",
    "JIRA_CONNECTOR",
    "CONFLUENCE_CONNECTOR",
    "CLICKUP_CONNECTOR",
    "GOOGLE_CALENDAR_CONNECTOR",
    "GOOGLE_GMAIL_CONNECTOR",
    "GOOGLE_DRIVE_CONNECTOR",
    "GOOGLE_DRIVE_FILE",
    "AIRTABLE_CONNECTOR",
    "CIRCLEBACK",
    "CIRCLEBACK_CONNECTOR",
    "COMPOSIO_GMAIL_CONNECTOR",
    "COMPOSIO_GOOGLE_CALENDAR_CONNECTOR",
    "TAVILY_API",
    "SEARXNG_API",
    "LINKUP_API",
    "BAIDU_SEARCH_API",
)

DOCUMENTTYPE_VALUES: tuple[str, ...] = (
    "EXTENSION",
    "CRAWLED_URL",
    "FILE",
    "OBSIDIAN_CONNECTOR",
    "NOTE",
    "COMPOSIO_GOOGLE_DRIVE_CONNECTOR",
)

SEARCHSOURCECONNECTORTYPE_VALUES: tuple[str, ...] = (
    "SERPER_API",
    "WEBCRAWLER_CONNECTOR",
    "OBSIDIAN_CONNECTOR",
    "MCP_CONNECTOR",
    "COMPOSIO_GOOGLE_DRIVE_CONNECTOR",
)

def _as_sql_enum(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    removed_values_sql = _as_sql_enum(REMOVED_VALUES)

    op.execute(
        f"""
        DELETE FROM documents
        WHERE document_type::text IN ({removed_values_sql});
        """
    )

    op.execute(
        f"""
        DELETE FROM search_source_connectors
        WHERE connector_type::text IN ({removed_values_sql});
        """
    )

    op.execute("ALTER TYPE documenttype RENAME TO documenttype_old")
    op.execute(
        f"CREATE TYPE documenttype AS ENUM ({_as_sql_enum(DOCUMENTTYPE_VALUES)})"
    )
    op.execute(
        "ALTER TABLE documents ALTER COLUMN document_type TYPE documenttype "
        "USING document_type::text::documenttype"
    )
    op.execute("DROP TYPE documenttype_old")

    op.execute("ALTER TYPE searchsourceconnectortype RENAME TO searchsourceconnectortype_old")
    op.execute(
        "CREATE TYPE searchsourceconnectortype AS ENUM ("
        f"{_as_sql_enum(SEARCHSOURCECONNECTORTYPE_VALUES)}"
        ")"
    )
    op.execute(
        "ALTER TABLE search_source_connectors ALTER COLUMN connector_type TYPE searchsourceconnectortype "
        "USING connector_type::text::searchsourceconnectortype"
    )
    op.execute("DROP TYPE searchsourceconnectortype_old")


def downgrade() -> None:
    # Enum hard-removal is not safely reversible.
    pass
