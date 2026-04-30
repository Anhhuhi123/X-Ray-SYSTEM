"""Rename surfsense_docs tables to nfd_docs

Revision ID: 120
Revises: 115
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "120"
down_revision: str | None = "115"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename surfsense_docs_documents and surfsense_docs_chunks tables to nfd_docs_*"""

    # Rename surfsense_docs_documents table first (before renaming chunks, since chunks references it)
    op.execute("ALTER TABLE surfsense_docs_documents RENAME TO nfd_docs_documents")

    # Rename indexes on nfd_docs_documents - only if they exist
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_surfsense_docs_documents_source') THEN
                ALTER INDEX ix_surfsense_docs_documents_source RENAME TO ix_nfd_docs_documents_source;
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_surfsense_docs_documents_content_hash') THEN
                ALTER INDEX ix_surfsense_docs_documents_content_hash RENAME TO ix_nfd_docs_documents_content_hash;
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_surfsense_docs_documents_updated_at') THEN
                ALTER INDEX ix_surfsense_docs_documents_updated_at RENAME TO ix_nfd_docs_documents_updated_at;
            END IF;
        END$$;
        """
    )

    # Rename the pg_trgm index on nfd_docs_documents - only if it exists
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_surfsense_docs_title_trgm') THEN
                ALTER INDEX idx_surfsense_docs_title_trgm RENAME TO idx_nfd_docs_title_trgm;
            END IF;
        END$$;
        """
    )

    # Now rename surfsense_docs_chunks table
    op.execute("ALTER TABLE surfsense_docs_chunks RENAME TO nfd_docs_chunks")

    # Rename index on nfd_docs_chunks - only if it exists
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_surfsense_docs_chunks_document_id') THEN
                ALTER INDEX ix_surfsense_docs_chunks_document_id RENAME TO ix_nfd_docs_chunks_document_id;
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    """Rename nfd_docs_* tables back to surfsense_docs_*"""

    # Rename index on nfd_docs_chunks back - only if it exists
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_nfd_docs_chunks_document_id') THEN
                ALTER INDEX ix_nfd_docs_chunks_document_id RENAME TO ix_surfsense_docs_chunks_document_id;
            END IF;
        END$$;
        """
    )

    # Rename nfd_docs_chunks table back
    op.execute("ALTER TABLE nfd_docs_chunks RENAME TO surfsense_docs_chunks")

    # Rename the pg_trgm index back - only if it exists
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_nfd_docs_title_trgm') THEN
                ALTER INDEX idx_nfd_docs_title_trgm RENAME TO idx_surfsense_docs_title_trgm;
            END IF;
        END$$;
        """
    )

    # Rename indexes on nfd_docs_documents back - only if they exist
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_nfd_docs_documents_updated_at') THEN
                ALTER INDEX ix_nfd_docs_documents_updated_at RENAME TO ix_surfsense_docs_documents_updated_at;
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_nfd_docs_documents_content_hash') THEN
                ALTER INDEX ix_nfd_docs_documents_content_hash RENAME TO ix_surfsense_docs_documents_content_hash;
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_nfd_docs_documents_source') THEN
                ALTER INDEX ix_nfd_docs_documents_source RENAME TO ix_surfsense_docs_documents_source;
            END IF;
        END$$;
        """
    )

    # Rename nfd_docs_documents table back
    op.execute("ALTER TABLE nfd_docs_documents RENAME TO surfsense_docs_documents")
