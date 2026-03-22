"""Multi-signal topic candidate scoring (Phase 3)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from storydiff.analysis.settings import AnalysisSettings
from storydiff.db.models import Article, ArticleEntity, Topic, TopicArticleLink


def cosine_distance_from_dot(article_vec: Sequence[float], other_vec: Sequence[float]) -> float:
    """Assume L2-normalized vectors; distance in ``[0, 1]`` for typical text embeddings."""
    dot = sum(a * b for a, b in zip(article_vec, other_vec, strict=True))
    return max(0.0, min(1.0, 1.0 - float(dot)))


def _exp_decay_hours(delta_hours: float, scale: float) -> float:
    if delta_hours < 0:
        delta_hours = 0.0
    return math.exp(-delta_hours / scale)


@dataclass(frozen=True)
class TopicSignals:
    vector_similarity: float
    entity_overlap: float
    category_match: float
    time_proximity: float
    topic_recency: float
    source_diversity: float


def _norm_key(raw: str | None, fallback: str) -> str:
    s = (raw or "").strip().lower()
    return s if s else fallback.strip().lower()


def topic_entity_normalized_set(session: Session, topic_id: int, *, sample_limit: int) -> set[str]:
    """Normalized entity strings from a sample of recent articles linked to the topic."""
    aid_rows = list(
        session.scalars(
            select(TopicArticleLink.article_id)
            .where(TopicArticleLink.topic_id == topic_id)
            .order_by(TopicArticleLink.assigned_at.desc())
            .limit(sample_limit)
        ).all()
    )
    if not aid_rows:
        return set()
    rows = session.execute(
        select(ArticleEntity.normalized_entity, ArticleEntity.entity_text).where(
            ArticleEntity.article_id.in_(aid_rows)
        )
    ).all()
    out: set[str] = set()
    for ne, et in rows:
        out.add(_norm_key(ne, str(et or "")))
    out.discard("")
    return out


def article_entity_normalized_set(entities: list[dict]) -> set[str]:
    s: set[str] = set()
    for e in entities:
        ne = e.get("normalized_entity")
        et = e.get("entity_text") or ""
        key = _norm_key(ne if isinstance(ne, str) else None, str(et))
        if key:
            s.add(key)
    return s


def entity_overlap_score(article_ents: set[str], topic_ents: set[str]) -> float:
    if not article_ents or not topic_ents:
        return 0.0
    inter = len(article_ents & topic_ents)
    union = len(article_ents | topic_ents)
    return float(inter) / float(union) if union else 0.0


def source_diversity_score(
    session: Session,
    topic_id: int,
    article: Article,
    *,
    sample_limit: int,
) -> float:
    """How well the article's outlet adds to topic outlet diversity (0–1)."""
    aids = list(
        session.scalars(
            select(TopicArticleLink.article_id)
            .where(TopicArticleLink.topic_id == topic_id)
            .order_by(TopicArticleLink.assigned_at.desc())
            .limit(sample_limit)
        ).all()
    )
    outlets: set[int] = set()
    for aid in aids:
        a = session.get(Article, aid)
        if a is not None:
            outlets.add(int(a.media_outlet_id))
    has_outlet = int(article.media_outlet_id) in outlets
    n = len(outlets)
    # Reward more diverse topics; reward new outlet slightly
    if n == 0:
        return 0.5
    div = min(1.0, n / 10.0)
    bonus = 0.15 if not has_outlet else 0.0
    return min(1.0, div + bonus)


def compute_signals(
    session: Session,
    *,
    article: Article,
    article_entities: list[dict],
    topic: Topic,
    vector_similarity: float,
    cfg: AnalysisSettings,
    now: datetime | None = None,
) -> TopicSignals:
    """Compute raw feature signals in ``[0, 1]``."""
    now = now or datetime.now(timezone.utc)
    a_ents = article_entity_normalized_set(article_entities)
    t_ents = topic_entity_normalized_set(
        session, int(topic.id), sample_limit=cfg.topic_entity_sample_size
    )
    eov = entity_overlap_score(a_ents, t_ents)
    cat = 1.0 if article.category_id is not None and article.category_id == topic.category_id else 0.0
    pub = article.published_at
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    else:
        pub = pub.astimezone(timezone.utc)
    ls = topic.last_seen_at
    if ls.tzinfo is None:
        ls = ls.replace(tzinfo=timezone.utc)
    else:
        ls = ls.astimezone(timezone.utc)
    delta_h = abs((pub - ls).total_seconds()) / 3600.0
    time_p = _exp_decay_hours(delta_h, 72.0)
    age_s = (now - ls).total_seconds()
    rec = math.exp(-max(0.0, age_s) / (7.0 * 24.0 * 3600.0))
    sd = source_diversity_score(session, int(topic.id), article, sample_limit=cfg.topic_entity_sample_size)
    return TopicSignals(
        vector_similarity=max(0.0, min(1.0, float(vector_similarity))),
        entity_overlap=eov,
        category_match=cat,
        time_proximity=time_p,
        topic_recency=rec,
        source_diversity=sd,
    )


def weighted_sum_score(signals: TopicSignals, cfg: AnalysisSettings) -> float:
    wv = cfg.topic_weight_vector
    we = cfg.topic_weight_entities
    wc = cfg.topic_weight_category
    wt = cfg.topic_weight_time
    wr = cfg.topic_weight_recency
    ws = cfg.topic_weight_source_diversity
    wsum = wv + we + wc + wt + wr + ws
    if wsum <= 0:
        return 0.0
    return (
        wv * signals.vector_similarity
        + we * signals.entity_overlap
        + wc * signals.category_match
        + wt * signals.time_proximity
        + wr * signals.topic_recency
        + ws * signals.source_diversity
    ) / wsum
