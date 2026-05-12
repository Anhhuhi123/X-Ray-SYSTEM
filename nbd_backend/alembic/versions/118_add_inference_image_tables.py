"""Add inference image tables for multi-label prediction history.

Revision ID: 118
Revises: 117
Create Date: 2026-05-12

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "118"
down_revision: str | None = "117"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'inference_requests'
            ) THEN
                CREATE TABLE inference_requests (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                    image_path TEXT NOT NULL,
                    model_name VARCHAR(100),
                    model_version VARCHAR(50),
                    inference_time_ms DOUBLE PRECISION,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            END IF;
        END$$;
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_inference_requests_user_id
        ON inference_requests (user_id);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_inference_requests_created_at
        ON inference_requests (created_at);
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'inference_predictions'
            ) THEN
                CREATE TABLE inference_predictions (
                    id UUID PRIMARY KEY,
                    request_id UUID NOT NULL REFERENCES inference_requests(id) ON DELETE CASCADE,
                    label_name VARCHAR(100) NOT NULL,
                    probability DOUBLE PRECISION NOT NULL,
                    threshold_used DOUBLE PRECISION NOT NULL,
                    is_positive BOOLEAN NOT NULL
                );
            END IF;
        END$$;
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_inference_predictions_request_id
        ON inference_predictions (request_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_inference_predictions_request_id")
    op.execute("DROP TABLE IF EXISTS inference_predictions")
    op.execute("DROP INDEX IF EXISTS ix_inference_requests_created_at")
    op.execute("DROP INDEX IF EXISTS ix_inference_requests_user_id")
    op.execute("DROP TABLE IF EXISTS inference_requests")
