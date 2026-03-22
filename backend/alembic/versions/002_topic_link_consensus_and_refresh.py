"""Topic link consensus fields and refresh timestamp on topics.

Revision ID: 002_topic_link_consensus
Revises: 001_phase1_initial
Create Date: 2026-03-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_topic_link_consensus"
down_revision: Union[str, None] = "001_phase1_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "topic_article_links",
        sa.Column("consensus_distance", sa.Numeric(precision=6, scale=4), nullable=True),
    )
    op.add_column(
        "topic_article_links",
        sa.Column("consensus_distance_topic_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "topics",
        sa.Column("last_consensus_refresh_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("topics", "last_consensus_refresh_at")
    op.drop_column("topic_article_links", "consensus_distance_topic_version")
    op.drop_column("topic_article_links", "consensus_distance")
