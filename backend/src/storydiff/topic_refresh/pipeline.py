"""Recompute topic consensus, update Qdrant, backfill link distances."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from storydiff.analysis.embeddings import EmbeddingService
from storydiff.analysis.json_utils import parse_json_object
from storydiff.analysis.llm import build_chat_client
from storydiff.analysis.prompts import CONSENSUS_REFRESH_SYSTEM
from storydiff.analysis.settings import load_analysis_settings
from storydiff.analysis.topic_qdrant import (
    retrieve_article_vector,
    retrieve_topic_vector,
    upsert_topic_embedding,
)
from storydiff.analysis.topic_scoring import cosine_distance_from_dot
from storydiff.db.models import Article, ArticleAnalysis, Topic, TopicArticleLink, TopicVersion
from storydiff.db.session import get_session_local
from storydiff.qdrant.settings import load_qdrant_settings

logger = logging.getLogger(__name__)


def _backfill_link_distances(
    session: Session,
    qclient: QdrantClient,
    *,
    topic_collection: str,
    article_collection: str,
    topic_id: int,
    consensus_version: int,
    vector_size: int,
) -> None:
    links = session.scalars(
        select(TopicArticleLink).where(TopicArticleLink.topic_id == topic_id)
    ).all()
    tvec = retrieve_topic_vector(qclient, topic_collection, topic_id)
    if tvec is None or len(tvec) != vector_size:
        logger.warning("topic_refresh backfill skipped: missing topic vector topic_id=%s", topic_id)
        return
    for link in links:
        av = retrieve_article_vector(qclient, article_collection, link.article_id)
        if av is None or len(av) != vector_size:
            continue
        link.consensus_distance = cosine_distance_from_dot(av, tvec)
        link.consensus_distance_topic_version = consensus_version


def process_topic_refresh(topic_id: int) -> dict[str, Any]:
    """Load topic with lock, recompute consensus within window, upsert Qdrant, backfill links."""
    analysis_settings = load_analysis_settings()
    qcfg = load_qdrant_settings()
    SessionLocal = get_session_local()
    session = SessionLocal()
    qclient = QdrantClient(url=qcfg.url, api_key=qcfg.api_key)
    embedder = EmbeddingService(qcfg.vector_size, analysis_settings)
    llm = build_chat_client(analysis_settings)
    now = datetime.now(timezone.utc)
    try:
        topic = session.scalar(
            select(Topic).where(Topic.id == topic_id).with_for_update()
        )
        if topic is None:
            return {"ok": False, "error": "topic_not_found"}

        if topic.last_consensus_refresh_at is not None:
            ref = topic.last_consensus_refresh_at
            if ref.tzinfo is None:
                ref = ref.replace(tzinfo=timezone.utc)
            else:
                ref = ref.astimezone(timezone.utc)
            elapsed = (now - ref).total_seconds()
            if elapsed < analysis_settings.topic_refresh_cooldown_seconds:
                return {"ok": True, "skipped": "cooldown"}

        window = timedelta(hours=analysis_settings.topic_refresh_window_hours)
        cutoff = now - window
        rows = session.execute(
            select(
                Article.id,
                Article.title,
                Article.snippet,
                Article.media_outlet_id,
                Article.published_at,
            )
            .join(TopicArticleLink, TopicArticleLink.article_id == Article.id)
            .where(TopicArticleLink.topic_id == topic_id, Article.published_at >= cutoff)
        ).all()
        if len(rows) < analysis_settings.topic_refresh_min_evidence:
            return {"ok": True, "skipped": "min_evidence"}

        lines = []
        article_ids: list[int] = []
        outlets: set[int] = set()
        for rid, title, snip, moid, _pub in rows:
            article_ids.append(int(rid))
            outlets.add(int(moid))
            t = (title or "")[:200]
            s = (snip or "")[:400]
            lines.append(f"- {t} | {s}")

        user = "Articles (same topic):\n" + "\n".join(lines[:80])
        raw = llm.complete_json_system_user(CONSENSUS_REFRESH_SYSTEM, user)
        data = parse_json_object(raw)
        title = str(data.get("title") or topic.current_title)[:500]
        summary = data.get("summary")
        summary_s = str(summary)[:4000] if summary is not None else None

        rel_scores: list[float] = []
        for aid in article_ids:
            row = session.get(ArticleAnalysis, aid)
            if row is not None and row.reliability_score is not None:
                rel_scores.append(float(row.reliability_score))
        rel_avg = sum(rel_scores) / len(rel_scores) if rel_scores else None

        old_v = int(topic.current_consensus_version)
        new_v = old_v + 1

        session.add(
            TopicVersion(
                topic_id=topic_id,
                version_no=new_v,
                title=title,
                summary=summary_s,
                reliability_score=rel_avg,
                article_count=len(article_ids),
                source_count=len(outlets),
                generated_at=now,
            )
        )
        topic.current_title = title
        topic.current_summary = summary_s
        topic.current_reliability_score = rel_avg
        topic.current_consensus_version = new_v
        topic.article_count = len(article_ids)
        topic.source_count = len(outlets)
        pubs_norm: list[datetime] = []
        for r in rows:
            p = r[4]
            if p is None:
                continue
            if p.tzinfo is None:
                p = p.replace(tzinfo=timezone.utc)
            else:
                p = p.astimezone(timezone.utc)
            pubs_norm.append(p)
        if pubs_norm:
            latest_art = max(pubs_norm)
            tls = topic.last_seen_at
            if tls.tzinfo is None:
                tls = tls.replace(tzinfo=timezone.utc)
            else:
                tls = tls.astimezone(timezone.utc)
            topic.last_seen_at = max(tls, latest_art)
        topic.updated_at = now
        topic.last_consensus_refresh_at = now
        session.flush()

        embed_text = f"{title}\n\n{summary_s or ''}".strip() or title
        vec = embedder.embed_text(embed_text)
        upsert_topic_embedding(qclient, qcfg.topic_collection, topic, vec, qcfg.vector_size)

        _backfill_link_distances(
            session,
            qclient,
            topic_collection=qcfg.topic_collection,
            article_collection=qcfg.article_collection,
            topic_id=topic_id,
            consensus_version=new_v,
            vector_size=qcfg.vector_size,
        )
        session.commit()
        logger.info("topic_refresh topic_id=%s version=%s ok", topic_id, new_v)
        return {"ok": True, "version": new_v}
    except Exception:
        logger.exception("topic_refresh failed topic_id=%s", topic_id)
        session.rollback()
        raise
    finally:
        session.close()


def process_topic_refresh_swallow(topic_id: int) -> dict[str, Any]:
    try:
        return process_topic_refresh(topic_id)
    except Exception as e:
        return {"ok": False, "error": str(e)}
