"""Phase 1 initial relational schema and indexes.

Revision ID: 001_phase1_initial
Revises:
Create Date: 2026-03-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_phase1_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_outlets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("domain"),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "articles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_article_id", sa.String(length=255), nullable=True),
        sa.Column("media_outlet_id", sa.BigInteger(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=20), server_default=sa.text("'en'"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source_category", sa.String(length=255), nullable=True),
        sa.Column("article_fingerprint", sa.String(length=255), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(length=50),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("topic_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
        ),
        sa.ForeignKeyConstraint(
            ["media_outlet_id"],
            ["media_outlets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_table(
        "article_analysis",
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("consensus_distance", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("framing_polarity", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("source_diversity_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("novel_claim_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("reliability_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("polarity_labels_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("article_id"),
    )
    op.create_table(
        "article_entities",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("entity_text", sa.Text(), nullable=False),
        sa.Column("normalized_entity", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("salience_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "topics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("canonical_label", sa.Text(), nullable=False),
        sa.Column("current_title", sa.Text(), nullable=False),
        sa.Column("current_summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("article_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("source_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("current_reliability_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column(
            "current_consensus_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "topic_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("reliability_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("article_count", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic_id", "version_no", name="uq_topic_versions_topic_version"),
    )
    op.create_table(
        "topic_article_links",
        sa.Column("topic_id", sa.BigInteger(), nullable=False),
        sa.Column("article_id", sa.BigInteger(), nullable=False),
        sa.Column("assignment_confidence", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("assignment_reason_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("topic_id", "article_id"),
    )
    op.create_table(
        "media_aggregates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("media_outlet_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("article_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("avg_consensus_distance", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("avg_framing_polarity", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("avg_source_diversity_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("avg_novel_claim_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("avg_reliability_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("composite_rank_score", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
        ),
        sa.ForeignKeyConstraint(
            ["media_outlet_id"],
            ["media_outlets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "api_request_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("route", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_articles_media_outlet_id", "articles", ["media_outlet_id"], unique=False)
    op.create_index("idx_articles_category_id", "articles", ["category_id"], unique=False)
    op.create_index("idx_articles_topic_id", "articles", ["topic_id"], unique=False)
    op.create_index(
        "idx_articles_published_at",
        "articles",
        ["published_at"],
        unique=False,
        postgresql_ops={"published_at": "DESC"},
    )
    op.create_index(
        "idx_articles_processing_status",
        "articles",
        ["processing_status"],
        unique=False,
    )
    op.create_index(
        "idx_article_entities_article_id",
        "article_entities",
        ["article_id"],
        unique=False,
    )
    op.create_index(
        "idx_article_entities_normalized_entity",
        "article_entities",
        ["normalized_entity"],
        unique=False,
    )
    op.create_index("idx_topics_category_id", "topics", ["category_id"], unique=False)
    op.create_index("idx_topics_status", "topics", ["status"], unique=False)
    op.create_index(
        "idx_topics_last_seen_at",
        "topics",
        ["last_seen_at"],
        unique=False,
        postgresql_ops={"last_seen_at": "DESC"},
    )
    op.create_index(
        "idx_topic_versions_topic_id",
        "topic_versions",
        ["topic_id"],
        unique=False,
    )
    op.create_index(
        "idx_topic_versions_generated_at",
        "topic_versions",
        ["generated_at"],
        unique=False,
        postgresql_ops={"generated_at": "DESC"},
    )
    op.create_index(
        "idx_topic_article_links_article_id",
        "topic_article_links",
        ["article_id"],
        unique=False,
    )
    op.create_index(
        "idx_topic_article_links_assignment_confidence",
        "topic_article_links",
        ["assignment_confidence"],
        unique=False,
    )
    op.create_index(
        "idx_media_aggregates_media_outlet_id",
        "media_aggregates",
        ["media_outlet_id"],
        unique=False,
    )
    op.create_index(
        "idx_media_aggregates_category_id",
        "media_aggregates",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        "idx_media_aggregates_window_start_end",
        "media_aggregates",
        ["window_start", "window_end"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_media_aggregates_window_start_end", table_name="media_aggregates")
    op.drop_index("idx_media_aggregates_category_id", table_name="media_aggregates")
    op.drop_index("idx_media_aggregates_media_outlet_id", table_name="media_aggregates")
    op.drop_index(
        "idx_topic_article_links_assignment_confidence",
        table_name="topic_article_links",
    )
    op.drop_index("idx_topic_article_links_article_id", table_name="topic_article_links")
    op.drop_index("idx_topic_versions_generated_at", table_name="topic_versions")
    op.drop_index("idx_topic_versions_topic_id", table_name="topic_versions")
    op.drop_index("idx_topics_last_seen_at", table_name="topics")
    op.drop_index("idx_topics_status", table_name="topics")
    op.drop_index("idx_topics_category_id", table_name="topics")
    op.drop_index("idx_article_entities_normalized_entity", table_name="article_entities")
    op.drop_index("idx_article_entities_article_id", table_name="article_entities")
    op.drop_index("idx_articles_processing_status", table_name="articles")
    op.drop_index("idx_articles_published_at", table_name="articles")
    op.drop_index("idx_articles_topic_id", table_name="articles")
    op.drop_index("idx_articles_category_id", table_name="articles")
    op.drop_index("idx_articles_media_outlet_id", table_name="articles")

    op.drop_table("api_request_logs")
    op.drop_table("media_aggregates")
    op.drop_table("topic_article_links")
    op.drop_table("topic_versions")
    op.drop_table("article_entities")
    op.drop_table("article_analysis")
    op.drop_table("topics")
    op.drop_table("articles")
    op.drop_table("categories")
    op.drop_table("media_outlets")
