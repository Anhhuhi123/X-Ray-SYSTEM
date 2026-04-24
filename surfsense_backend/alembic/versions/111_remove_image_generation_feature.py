"""Remove image generation feature schema

Revision ID: 111
Revises: 110
Create Date: 2026-04-24

This migration removes image-generation schema objects that are no longer used:
- image_generations table
- image_generation_configs table
- searchspaces.image_generation_config_id column
- imagegenprovider enum type

It also removes image generation permissions from existing role rows.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "111"
down_revision: str | None = "110"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


IMAGE_PROVIDER_ENUM = "imagegenprovider"
IMAGE_CONFIG_TABLE = "image_generation_configs"
IMAGE_GENERATIONS_TABLE = "image_generations"
SEARCHSPACES_TABLE = "searchspaces"


def _table_exists(conn: sa.Connection, table_name: str) -> bool:
    return (
        conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.tables WHERE table_name = :table_name"
            ),
            {"table_name": table_name},
        ).fetchone()
        is not None
    )


def _column_exists(conn: sa.Connection, table_name: str, column_name: str) -> bool:
    return (
        conn.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = :table_name AND column_name = :column_name
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).fetchone()
        is not None
    )


def _constraint_exists(conn: sa.Connection, table_name: str, constraint_name: str) -> bool:
    return (
        conn.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.table_constraints
                WHERE table_name = :table_name AND constraint_name = :constraint_name
                """
            ),
            {"table_name": table_name, "constraint_name": constraint_name},
        ).fetchone()
        is not None
    )


def _enum_exists(conn: sa.Connection, enum_name: str) -> bool:
    return (
        conn.execute(
            sa.text("SELECT 1 FROM pg_type WHERE typname = :enum_name"),
            {"enum_name": enum_name},
        ).fetchone()
        is not None
    )


def upgrade() -> None:
    conn = op.get_bind()

    # Remove image generation permissions from all role rows.
    if _table_exists(conn, "search_space_roles"):
        op.execute(
            """
            UPDATE search_space_roles
            SET permissions = array_remove(
                array_remove(
                    array_remove(permissions, 'image_generations:create'),
                    'image_generations:read'
                ),
                'image_generations:delete'
            )
            WHERE permissions IS NOT NULL
            """
        )

    if _column_exists(conn, SEARCHSPACES_TABLE, "image_generation_config_id"):
        op.drop_column(SEARCHSPACES_TABLE, "image_generation_config_id")

    if _table_exists(conn, IMAGE_GENERATIONS_TABLE):
        op.execute("DROP INDEX IF EXISTS ix_image_generations_access_token")
        op.execute("DROP INDEX IF EXISTS ix_image_generations_created_at")
        op.execute("DROP INDEX IF EXISTS ix_image_generations_created_by_id")
        op.execute("DROP INDEX IF EXISTS ix_image_generations_search_space_id")
        op.drop_table(IMAGE_GENERATIONS_TABLE)

    if _table_exists(conn, IMAGE_CONFIG_TABLE):
        op.execute("DROP INDEX IF EXISTS ix_image_generation_configs_user_id")
        op.execute("DROP INDEX IF EXISTS ix_image_generation_configs_search_space_id")
        op.execute("DROP INDEX IF EXISTS ix_image_generation_configs_name")
        op.drop_table(IMAGE_CONFIG_TABLE)

    if _enum_exists(conn, IMAGE_PROVIDER_ENUM):
        postgresql.ENUM(name=IMAGE_PROVIDER_ENUM).drop(conn, checkfirst=True)


def downgrade() -> None:
    conn = op.get_bind()

    if not _enum_exists(conn, IMAGE_PROVIDER_ENUM):
        image_provider_enum = postgresql.ENUM(
            "OPENAI",
            "AZURE_OPENAI",
            "GOOGLE",
            "VERTEX_AI",
            "BEDROCK",
            "RECRAFT",
            "OPENROUTER",
            "XINFERENCE",
            "NSCALE",
            name=IMAGE_PROVIDER_ENUM,
            create_type=False,
        )
        image_provider_enum.create(conn, checkfirst=True)

    if not _column_exists(conn, SEARCHSPACES_TABLE, "image_generation_config_id"):
        op.add_column(
            SEARCHSPACES_TABLE,
            sa.Column(
                "image_generation_config_id",
                sa.Integer(),
                nullable=True,
                server_default="0",
            ),
        )

    if not _table_exists(conn, IMAGE_CONFIG_TABLE):
        op.create_table(
            IMAGE_CONFIG_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "name",
                sa.String(length=100),
                nullable=False,
            ),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column(
                "provider",
                postgresql.ENUM(name=IMAGE_PROVIDER_ENUM, create_type=False),
                nullable=False,
            ),
            sa.Column("custom_provider", sa.String(length=100), nullable=True),
            sa.Column("model_name", sa.String(length=100), nullable=False),
            sa.Column("api_key", sa.String(), nullable=False),
            sa.Column("api_base", sa.String(length=500), nullable=True),
            sa.Column("api_version", sa.String(length=50), nullable=True),
            sa.Column("litellm_params", sa.JSON(), nullable=True),
            sa.Column(
                "search_space_id",
                sa.Integer(),
                sa.ForeignKey("searchspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("user.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_image_generation_configs_name",
            IMAGE_CONFIG_TABLE,
            ["name"],
        )
        op.create_index(
            "ix_image_generation_configs_search_space_id",
            IMAGE_CONFIG_TABLE,
            ["search_space_id"],
        )
        op.create_index(
            "ix_image_generation_configs_user_id",
            IMAGE_CONFIG_TABLE,
            ["user_id"],
        )

    if not _table_exists(conn, IMAGE_GENERATIONS_TABLE):
        op.create_table(
            IMAGE_GENERATIONS_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("model", sa.String(length=200), nullable=True),
            sa.Column("n", sa.Integer(), nullable=True),
            sa.Column("quality", sa.String(length=50), nullable=True),
            sa.Column("size", sa.String(length=50), nullable=True),
            sa.Column("style", sa.String(length=50), nullable=True),
            sa.Column("response_format", sa.String(length=50), nullable=True),
            sa.Column("image_generation_config_id", sa.Integer(), nullable=True),
            sa.Column("response_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("access_token", sa.String(length=64), nullable=True),
            sa.Column(
                "search_space_id",
                sa.Integer(),
                sa.ForeignKey("searchspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_by_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("user.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_image_generations_search_space_id",
            IMAGE_GENERATIONS_TABLE,
            ["search_space_id"],
        )
        op.create_index(
            "ix_image_generations_created_by_id",
            IMAGE_GENERATIONS_TABLE,
            ["created_by_id"],
        )
        op.create_index(
            "ix_image_generations_created_at",
            IMAGE_GENERATIONS_TABLE,
            ["created_at"],
        )
        op.create_index(
            "ix_image_generations_access_token",
            IMAGE_GENERATIONS_TABLE,
            ["access_token"],
        )

    # Restore permissions for default roles to match pre-removal behavior.
    if _table_exists(conn, "search_space_roles"):
        if _column_exists(conn, "search_space_roles", "name"):
            op.execute(
                """
                UPDATE search_space_roles
                SET permissions = permissions || ARRAY['image_generations:create', 'image_generations:read']
                WHERE name = 'Editor'
                  AND NOT ('image_generations:create' = ANY(permissions))
                """
            )
            op.execute(
                """
                UPDATE search_space_roles
                SET permissions = permissions || ARRAY['image_generations:read']
                WHERE name = 'Viewer'
                  AND NOT ('image_generations:read' = ANY(permissions))
                """
            )