from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storydiff.db.base import Base


class MediaOutlet(Base):
    __tablename__ = "media_outlets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_article_id: Mapped[Optional[str]] = mapped_column(String(255))
    media_outlet_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("media_outlets.id"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    snippet: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'en'"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    source_category: Mapped[Optional[str]] = mapped_column(String(255))
    article_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'pending'")
    )
    category_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("categories.id"))
    topic_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    analysis: Mapped[Optional["ArticleAnalysis"]] = relationship(
        back_populates="article", uselist=False, cascade="all, delete-orphan"
    )


class ArticleAnalysis(Base):
    __tablename__ = "article_analysis"

    article_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    summary: Mapped[Optional[str]] = mapped_column(Text)
    consensus_distance: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    framing_polarity: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    source_diversity_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    novel_claim_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    reliability_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    polarity_labels_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    article: Mapped["Article"] = relationship(back_populates="analysis")


class ArticleEntity(Base):
    __tablename__ = "article_entities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    entity_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_entity: Mapped[Optional[str]] = mapped_column(Text)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100))
    salience_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categories.id"), nullable=False)
    canonical_label: Mapped[str] = mapped_column(Text, nullable=False)
    current_title: Mapped[str] = mapped_column(Text, nullable=False)
    current_summary: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'active'"))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    current_reliability_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    current_consensus_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TopicVersion(Base):
    __tablename__ = "topic_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    reliability_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    article_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("topic_id", "version_no", name="uq_topic_versions_topic_version"),)


class TopicArticleLink(Base):
    __tablename__ = "topic_article_links"

    topic_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    article_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    assignment_confidence: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    assignment_reason_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MediaAggregate(Base):
    __tablename__ = "media_aggregates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    media_outlet_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("media_outlets.id"), nullable=False
    )
    category_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("categories.id"))
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    avg_consensus_distance: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    avg_framing_polarity: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    avg_source_diversity_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    avg_novel_claim_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    avg_reliability_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    composite_rank_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ApiRequestLog(Base):
    __tablename__ = "api_request_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    route: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
