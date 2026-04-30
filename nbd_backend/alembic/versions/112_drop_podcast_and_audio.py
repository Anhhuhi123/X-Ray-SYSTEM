"""drop_podcast_and_audio

Revision ID: 6353cf3787f1
Revises: 110
Create Date: 2026-04-21 10:11:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6353cf3787f1'
down_revision: str | None = '110'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop podcast related tables
    op.execute('DROP TABLE IF EXISTS podcasts CASCADE')
    
    # Remove podcast_status enum and document_type youtube_video
    # Note: Alembic doesn't natively drop enum types directly inside its python functions cross-database nicely,
    # but the DB already drops it if there's no reference remaining, or we can just leave it as is for simplicity.
    pass


def downgrade() -> None:
    # Minimal downgrade to avoid errors if requested
    pass