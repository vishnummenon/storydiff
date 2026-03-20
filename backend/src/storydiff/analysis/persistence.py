"""Postgres operations for article analysis runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from storydiff.db.models import Article, ArticleAnalysis, ArticleEntity


def set_processing_status(
    session: Session,
    article_id: int,
    status: str,
) -> None:
    now = datetime.now(timezone.utc)
    session.execute(
        update(Article)
        .where(Article.id == article_id)
        .values(processing_status=status, updated_at=now)
    )


def upsert_article_analysis(
    session: Session,
    *,
    article_id: int,
    summary: str | None,
    consensus_distance: float | None,
    framing_polarity: float | None,
    source_diversity_score: float | None,
    novel_claim_score: float | None,
    reliability_score: float | None,
    polarity_labels_json: dict[str, Any] | None,
    model_version: str,
    analyzed_at: datetime,
) -> None:
    row = session.get(ArticleAnalysis, article_id)
    if row is None:
        session.add(
            ArticleAnalysis(
                article_id=article_id,
                summary=summary,
                consensus_distance=consensus_distance,
                framing_polarity=framing_polarity,
                source_diversity_score=source_diversity_score,
                novel_claim_score=novel_claim_score,
                reliability_score=reliability_score,
                polarity_labels_json=polarity_labels_json,
                model_version=model_version,
                analyzed_at=analyzed_at,
            )
        )
    else:
        row.summary = summary
        row.consensus_distance = consensus_distance
        row.framing_polarity = framing_polarity
        row.source_diversity_score = source_diversity_score
        row.novel_claim_score = novel_claim_score
        row.reliability_score = reliability_score
        row.polarity_labels_json = polarity_labels_json
        row.model_version = model_version
        row.analyzed_at = analyzed_at
        row.updated_at = analyzed_at


def replace_article_entities(
    session: Session,
    article_id: int,
    entities: Sequence[dict[str, Any]],
) -> None:
    session.execute(delete(ArticleEntity).where(ArticleEntity.article_id == article_id))
    for e in entities:
        session.add(
            ArticleEntity(
                article_id=article_id,
                entity_text=str(e["entity_text"]),
                normalized_entity=e.get("normalized_entity"),
                entity_type=e.get("entity_type"),
                salience_score=e.get("salience_score"),
            )
        )


def update_article_category(
    session: Session,
    article_id: int,
    category_id: int | None,
) -> None:
    now = datetime.now(timezone.utc)
    session.execute(
        update(Article)
        .where(Article.id == article_id)
        .values(category_id=category_id, updated_at=now)
    )


def get_article_for_analysis(session: Session, article_id: int) -> Article | None:
    return session.scalar(select(Article).where(Article.id == article_id))
