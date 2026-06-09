"""remove_electric_replication

Revision ID: 9039a81d1e99
Revises: 120
Create Date: 2026-06-09 11:25:14.471645

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9039a81d1e99"
down_revision: str | None = "120"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop Electric SQL replication publication, user and reset replica identities."""
    # Drop publication
    op.execute("DROP PUBLICATION IF EXISTS electric_publication_default;")

    # Reset replica identity back to DEFAULT for replicated tables
    tables = [
        "notifications",
        "chat_session_state",
        "new_chat_messages",
        "chat_comments",
    ]
    for table in tables:
        op.execute(sa.text(f"ALTER TABLE {table} REPLICA IDENTITY DEFAULT;"))

    # Safely revoke privileges and drop the electric user
    op.execute(
        """
        DO $$
        DECLARE
            db_name TEXT;
        BEGIN
            IF EXISTS (SELECT FROM pg_user WHERE usename = 'electric') THEN
                -- Revoke default privileges
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM electric;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON SEQUENCES FROM electric;
                
                -- Revoke normal privileges
                REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM electric;
                REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM electric;
                REVOKE ALL PRIVILEGES ON SCHEMA public FROM electric;
                
                -- Revoke database access
                SELECT current_database() INTO db_name;
                EXECUTE format('REVOKE ALL PRIVILEGES ON DATABASE %I FROM electric', db_name);
                
                -- Drop the user
                DROP USER electric;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Re-create Electric SQL replication publication, user and set replica identities."""
    # Re-create electric user if not exists
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'electric') THEN
                CREATE USER electric WITH REPLICATION PASSWORD 'electric_password';
            END IF;
        END
        $$;
        """
    )

    # Grant privileges
    op.execute(
        """
        DO $$
        DECLARE
            db_name TEXT;
        BEGIN
            SELECT current_database() INTO db_name;
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO electric', db_name);
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO electric;")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO electric;")
    op.execute("GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO electric;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO electric;"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO electric;"
    )

    # Re-create publication
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_publication WHERE pubname = 'electric_publication_default') THEN
                CREATE PUBLICATION electric_publication_default;
            END IF;
        END
        $$;
        """
    )

    # Reset replica identity to FULL for replicated tables and add to publication
    tables = [
        "notifications",
        "chat_session_state",
        "new_chat_messages",
        "chat_comments",
    ]
    for table in tables:
        op.execute(sa.text(f"ALTER TABLE {table} REPLICA IDENTITY FULL;"))
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_publication_tables 
                    WHERE pubname = 'electric_publication_default' AND tablename = '{table}'
                ) THEN
                    ALTER PUBLICATION electric_publication_default ADD TABLE {table};
                END IF;
            END
            $$;
            """
        )
