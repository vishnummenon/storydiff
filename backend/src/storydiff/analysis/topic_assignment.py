"""Assign an analyzed article to an existing topic or create a new one."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Protocol

from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from storydiff.analysis.embeddings import EmbeddingService
from storydiff.analysis.persistence import get_or_create_category, set_article_topic
from storydiff.analysis.settings import AnalysisSettings
from storydiff.analysis.topic_qdrant import (
    retrieve_topic_vector,
    search_topic_candidates,
    upsert_topic_embedding,
)
from storydiff.analysis.topic_scoring import compute_signals, cosine_distance_from_dot, weighted_sum_score
from storydiff.db.models import Article, Topic
from storydiff.ingestion.publisher import utc_iso_z
from storydiff.qdrant.settings import QdrantSettings

logger = logging.getLogger(__name__)


class TopicRefreshPublisher(Protocol):
    def publish_topic_refresh(self, payload: dict[str, Any]) -> None: ...


def _emit_refresh(events: TopicRefreshPublisher, topic_id: int) -> None:
    try:
        events.publish_topic_refresh(
            {
                "event_type": "topic.refresh",
                "topic_id": topic_id,
                "emitted_at": utc_iso_z(),
            }
        )
    except Exception:
        logger.exception("topic.refresh publish failed topic_id=%s", topic_id)


def _ensure_category_id(session: Session, article: Article) -> None:
    if article.category_id is not None:
        return
    c = get_or_create_category(session, "uncategorized", "Uncategorized")
    article.category_id = c.id
    session.flush()


def assign_article_to_topic(
    session: Session,
    article: Article,
    embedding: list[float],
    entities: list[dict[str, Any]],
    summary: str | None,
    *,
    qclient: QdrantClient,
    qcfg: QdrantSettings,
    cfg: AnalysisSettings,
    embedder: EmbeddingService,
    events: TopicRefreshPublisher,
) -> dict[str, Any]:
    """
    Link ``article`` to best topic or create one. Returns state updates for the graph
    (``consensus_distance``, ``topic_id``).
    """
    _ensure_category_id(session, article)
    now = datetime.now(timezone.utc)

    candidates = search_topic_candidates(
        qclient,
        qcfg.topic_collection,
        embedding,
        limit=cfg.topic_candidate_top_n,
    )
    best: tuple[Topic, float, dict[str, Any]] | None = None
    for tid, sim in candidates:
        topic = session.get(Topic, tid)
        if topic is None or topic.status != "active":
            continue
        sig = compute_signals(
            session,
            article=article,
            article_entities=entities,
            topic=topic,
            vector_similarity=float(sim),
            cfg=cfg,
        )
        score = weighted_sum_score(sig, cfg)
        reason = {
            "vector_similarity": sig.vector_similarity,
            "entity_overlap": sig.entity_overlap,
            "category_match": sig.category_match,
            "time_proximity": sig.time_proximity,
            "topic_recency": sig.topic_recency,
            "source_diversity": sig.source_diversity,
            "composite": score,
            "qdrant_similarity": sim,
        }
        if best is None or score > best[1]:
            best = (topic, score, reason)

    if best is not None and best[1] >= cfg.topic_assign_threshold:
        topic, score, reason = best
        tvec = retrieve_topic_vector(qclient, qcfg.topic_collection, int(topic.id))
        dist: float | None = None
        dist_ver: int | None = None
        if tvec is not None and len(tvec) == len(embedding):
            dist = cosine_distance_from_dot(embedding, tvec)
            dist_ver = int(topic.current_consensus_version)
        set_article_topic(
            session,
            article.id,
            topic.id,
            confidence=float(score),
            reason=reason,
            consensus_distance=dist,
            consensus_distance_topic_version=dist_ver,
        )
        if article.published_at.tzinfo is None:
            pub = article.published_at.replace(tzinfo=timezone.utc)
        else:
            pub = article.published_at.astimezone(timezone.utc)
        if topic.last_seen_at.tzinfo is None:
            tls = topic.last_seen_at.replace(tzinfo=timezone.utc)
        else:
            tls = topic.last_seen_at.astimezone(timezone.utc)
        topic.last_seen_at = max(tls, pub)
        topic.updated_at = now
        session.flush()
        _emit_refresh(events, int(topic.id))
        return {
            "topic_id": int(topic.id),
            "consensus_distance": dist,
        }

    # New topic
    title = (article.title or "")[:500]
    summ = (summary or "")[:2000]
    topic_text = f"{title}\n\n{summ}".strip() or title
    tvec_new = embedder.embed_text(topic_text)
    topic = Topic(
        category_id=int(article.category_id),
        canonical_label="pending",
        current_title=title,
        current_summary=summ or None,
        status="active",
        first_seen_at=article.published_at,
        last_seen_at=article.published_at,
        article_count=1,
        source_count=1,
        current_reliability_score=None,
        current_consensus_version=1,
    )
    session.add(topic)
    session.flush()
    topic.canonical_label = f"topic-{topic.id}"
    upsert_topic_embedding(qclient, qcfg.topic_collection, topic, tvec_new, qcfg.vector_size)
    dist_new: float | None = None
    dist_ver_new: int | None = None
    if len(embedding) == len(tvec_new):
        dist_new = cosine_distance_from_dot(embedding, tvec_new)
        dist_ver_new = int(topic.current_consensus_version)
    conf = max(0.0, min(1.0, float(best[1]) if best else 0.35))
    reason_new: dict[str, Any] = (
        {**best[2], "created": True, "below_threshold": True} if best else {"created": True, "reason": "no_candidates"}
    )
    set_article_topic(
        session,
        article.id,
        topic.id,
        confidence=conf,
        reason=reason_new,
        consensus_distance=dist_new,
        consensus_distance_topic_version=dist_ver_new,
    )
    session.flush()
    _emit_refresh(events, int(topic.id))
    return {
        "topic_id": int(topic.id),
        "consensus_distance": dist_new,
    }
