"""104_add_notification_composite_indexes

Revision ID: 104
Revises: 103
Create Date: 2026-03-10

Add composite indexes on the notifications table to speed up the
most common query patterns:
  - Unread count by user/category: (user_id, read, type, created_at)
  - Notification list by user/space: (user_id, search_space_id, created_at)
  - Single-column index on type (for category filtering)
  - Single-column index on search_space_id (for space filtering)
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "104"
down_revision: str | None = "103"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename = 'notifications'
                  AND indexname = 'ix_notifications_user_read_type_created'
            ) THEN
                CREATE INDEX ix_notifications_user_read_type_created
                ON notifications (user_id, read, type, created_at);
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename = 'notifications'
                  AND indexname = 'ix_notifications_user_space_created'
            ) THEN
                CREATE INDEX ix_notifications_user_space_created
                ON notifications (user_id, search_space_id, created_at);
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename = 'notifications'
                  AND indexname = 'ix_notifications_type'
            ) THEN
                CREATE INDEX ix_notifications_type ON notifications (type);
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename = 'notifications'
                  AND indexname = 'ix_notifications_search_space_id'
            ) THEN
                CREATE INDEX ix_notifications_search_space_id
                ON notifications (search_space_id);
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_notifications_search_space_id")
    op.execute("DROP INDEX IF EXISTS ix_notifications_type")
    op.execute("DROP INDEX IF EXISTS ix_notifications_user_space_created")
    op.execute("DROP INDEX IF EXISTS ix_notifications_user_read_type_created")
