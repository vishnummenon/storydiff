"""Add GIN expression indexes for full-text search on articles and topics.

Revision ID: 003_add_fts_indexes
Revises: 002_topic_link_consensus
Create Date: 2026-03-29

"""

from typing import Sequence, Union

from alembic import op

revision: str = "003_add_fts_indexes"
down_revision: Union[str, None] = "002_topic_link_consensus"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX idx_articles_fts ON articles "
        "USING GIN (to_tsvector('english', coalesce(title, '')))"
    )
    op.execute(
        "CREATE INDEX idx_topics_fts ON topics "
        "USING GIN (to_tsvector('english', coalesce(current_title,'') || ' ' || coalesce(current_summary,'')))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_topics_fts")
    op.execute("DROP INDEX IF EXISTS idx_articles_fts")
