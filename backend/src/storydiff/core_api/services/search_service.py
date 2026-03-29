"""Keyword, semantic, and hybrid search."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from qdrant_client import QdrantClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from storydiff.analysis.embeddings import EmbeddingService
from storydiff.core_api.util import merge_hybrid_scores
from storydiff.db.models import Article, Category, MediaOutlet, Topic
from storydiff.qdrant.settings import QdrantSettings, load_qdrant_settings


def _kw_topic(
    session: Session,
    q: str,
    category_slug: str | None,
    dt_from: datetime | None,
    dt_to: datetime | None,
    limit: int,
) -> list[dict[str, Any]]:
    fts = text(
        "to_tsvector('english', coalesce(current_title,'') || ' ' || coalesce(current_summary,''))"
        " @@ plainto_tsquery('english', :q)"
    ).bindparams(q=q)
    stmt = select(Topic).where(fts)
    if category_slug is not None:
        stmt = stmt.join(Category, Topic.category_id == Category.id).where(Category.slug == category_slug)
    if dt_from is not None:
        stmt = stmt.where(Topic.last_seen_at >= dt_from)
    if dt_to is not None:
        stmt = stmt.where(Topic.last_seen_at <= dt_to)
    stmt = stmt.order_by(Topic.last_seen_at.desc()).limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [
        {
            "topic_id": int(t.id),
            "title": t.current_title,
            "summary": t.current_summary,
            "score": 1.0,
        }
        for t in rows
    ]


def _kw_articles(
    session: Session,
    q: str,
    category_slug: str | None,
    dt_from: datetime | None,
    dt_to: datetime | None,
    limit: int,
) -> list[dict[str, Any]]:
    fts = text(
        "to_tsvector('english', coalesce(articles.title,'')) @@ plainto_tsquery('english', :q)"
    ).bindparams(q=q)
    stmt = (
        select(Article, MediaOutlet)
        .join(MediaOutlet, MediaOutlet.id == Article.media_outlet_id)
        .where(fts)
    )
    if category_slug:
        stmt = stmt.join(Category, Article.category_id == Category.id).where(Category.slug == category_slug)
    if dt_from is not None:
        stmt = stmt.where(Article.published_at >= dt_from)
    if dt_to is not None:
        stmt = stmt.where(Article.published_at <= dt_to)
    stmt = stmt.order_by(Article.published_at.desc()).limit(limit)
    out: list[dict[str, Any]] = []
    for art, mo in session.execute(stmt).all():
        out.append(
            {
                "article_id": int(art.id),
                "title": art.title,
                "url": art.url,
                "media_outlet": {
                    "id": int(mo.id),
                    "slug": mo.slug,
                    "name": mo.name,
                },
                "published_at": art.published_at.isoformat() if art.published_at else None,
                "score": 1.0,
            }
        )
    return out


def _semantic_topics(
    *,
    session: Session,
    qclient: QdrantClient,
    qcfg: QdrantSettings,
    embedding: EmbeddingService,
    q: str,
    category_slug: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    vec = embedding.embed_text(q)
    flt: Any = None
    if category_slug:
        cat = session.execute(select(Category).where(Category.slug == category_slug)).scalar_one_or_none()
        if cat is None:
            return []
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        flt = Filter(must=[FieldCondition(key="category_id", match=MatchValue(value=int(cat.id)))])

    hits = qclient.query_points(
        collection_name=qcfg.topic_collection,
        query=vec,
        limit=limit,
        with_payload=True,
        query_filter=flt,
    )
    out: list[dict[str, Any]] = []
    for h in hits:
        tid = h.payload.get("topic_id") if h.payload else None
        if tid is None:
            continue
        t = session.get(Topic, int(tid))
        if t is None:
            continue
        score = float(h.score) if h.score is not None else 0.0
        out.append(
            {
                "topic_id": int(t.id),
                "title": t.current_title,
                "summary": t.current_summary,
                "score": score,
            }
        )
    return out


def _semantic_articles(
    *,
    session: Session,
    qclient: QdrantClient,
    qcfg: QdrantSettings,
    embedding: EmbeddingService,
    q: str,
    category_slug: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    vec = embedding.embed_text(q)
    flt: Any = None
    if category_slug:
        cat = session.execute(select(Category).where(Category.slug == category_slug)).scalar_one_or_none()
        if cat is None:
            return []
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        flt = Filter(must=[FieldCondition(key="category_id", match=MatchValue(value=int(cat.id)))])

    hits = qclient.query_points(
        collection_name=qcfg.article_collection,
        query=vec,
        limit=limit,
        with_payload=True,
        query_filter=flt,
    )
    out: list[dict[str, Any]] = []
    for h in hits:
        aid = h.payload.get("article_id") if h.payload else None
        if aid is None:
            continue
        art = session.get(Article, int(aid))
        if art is None:
            continue
        mo = session.get(MediaOutlet, art.media_outlet_id)
        if mo is None:
            continue
        score = float(h.score) if h.score is not None else 0.0
        out.append(
            {
                "article_id": int(art.id),
                "title": art.title,
                "url": art.url,
                "media_outlet": {
                    "id": int(mo.id),
                    "slug": mo.slug,
                    "name": mo.name,
                },
                "published_at": art.published_at.isoformat() if art.published_at else None,
                "score": score,
            }
        )
    return out


def run_search(
    session: Session,
    *,
    q: str,
    mode: str,
    result_type: str,
    category_slug: str | None,
    dt_from: datetime | None,
    dt_to: datetime | None,
    limit: int,
    embedding: EmbeddingService | None,
    qclient: QdrantClient | None,
) -> dict[str, Any]:
    """Returns ``data`` inner object for search (query, mode, results)."""
    want_topics = result_type in ("topics", "all")
    want_articles = result_type in ("articles", "all")

    topics_out: list[dict[str, Any]] = []
    articles_out: list[dict[str, Any]] = []

    if mode == "keyword":
        if want_topics:
            topics_out = _kw_topic(session, q, category_slug, dt_from, dt_to, limit)
        if want_articles:
            articles_out = _kw_articles(session, q, category_slug, dt_from, dt_to, limit)
        return {
            "query": q,
            "mode": mode,
            "results": {"topics": topics_out, "articles": articles_out},
        }

    if qclient is None:
        raise RuntimeError("Semantic or hybrid search requires Qdrant (set QDRANT_URL)")

    if embedding is None:
        raise RuntimeError("Semantic or hybrid search requires embeddings (set EMBEDDING_VECTOR_SIZE)")

    qcfg = load_qdrant_settings()

    if mode == "semantic":
        if want_topics:
            topics_out = _semantic_topics(
                session=session,
                qclient=qclient,
                qcfg=qcfg,
                embedding=embedding,
                q=q,
                category_slug=category_slug,
                limit=limit,
            )
        if want_articles:
            articles_out = _semantic_articles(
                session=session,
                qclient=qclient,
                qcfg=qcfg,
                embedding=embedding,
                q=q,
                category_slug=category_slug,
                limit=limit,
            )
        return {
            "query": q,
            "mode": mode,
            "results": {"topics": topics_out, "articles": articles_out},
        }

    # hybrid: run both branches, merge scores by topic_id / article_id
    kw_t: dict[int, float] = {}
    kw_a: dict[int, float] = {}
    if want_topics:
        for t in _kw_topic(session, q, category_slug, dt_from, dt_to, limit * 2):
            kw_t[int(t["topic_id"])] = 1.0
    if want_articles:
        for a in _kw_articles(session, q, category_slug, dt_from, dt_to, limit * 2):
            kw_a[int(a["article_id"])] = 1.0

    sem_t: list[dict[str, Any]] = []
    sem_a: list[dict[str, Any]] = []
    if want_topics:
        sem_t = _semantic_topics(
            session=session,
            qclient=qclient,
            qcfg=qcfg,
            embedding=embedding,
            q=q,
            category_slug=category_slug,
            limit=limit * 2,
        )
    if want_articles:
        sem_a = _semantic_articles(
            session=session,
            qclient=qclient,
            qcfg=qcfg,
            embedding=embedding,
            q=q,
            category_slug=category_slug,
            limit=limit * 2,
        )

    # Normalize semantic scores to 0..1 per result set (cosine distance varies by metric)
    def _norm_sem(xs: list[dict[str, Any]]) -> dict[int, float]:
        if not xs:
            return {}
        scores = [float(x["score"]) for x in xs]
        lo, hi = min(scores), max(scores)
        if hi <= lo:
            return {int(x["topic_id" if "topic_id" in x else "article_id"]): 0.5 for x in xs}
        out: dict[int, float] = {}
        for x in xs:
            key = int(x["topic_id"]) if "topic_id" in x else int(x["article_id"])
            s = (float(x["score"]) - lo) / (hi - lo)
            out[key] = s
        return out

    nt = _norm_sem(sem_t)
    na = _norm_sem(sem_a)

    merged_topics: list[dict[str, Any]] = []
    if want_topics:
        seen: set[int] = set()
        for row in sem_t:
            tid = int(row["topic_id"])
            if tid in seen:
                continue
            seen.add(tid)
            ks = 1.0 if tid in kw_t else None
            ss = nt.get(tid)
            row = dict(row)
            row["score"] = merge_hybrid_scores(ks, ss)
            merged_topics.append(row)
        for row in _kw_topic(session, q, category_slug, dt_from, dt_to, limit * 2):
            tid = int(row["topic_id"])
            if tid in seen:
                continue
            seen.add(tid)
            row = dict(row)
            row["score"] = merge_hybrid_scores(1.0, None)
            merged_topics.append(row)
        merged_topics.sort(key=lambda x: float(x["score"]), reverse=True)
        merged_topics = merged_topics[:limit]

    merged_articles: list[dict[str, Any]] = []
    if want_articles:
        seen_a: set[int] = set()
        for row in sem_a:
            aid = int(row["article_id"])
            if aid in seen_a:
                continue
            seen_a.add(aid)
            ks = 1.0 if aid in kw_a else None
            ss = na.get(aid)
            row = dict(row)
            row["score"] = merge_hybrid_scores(ks, ss)
            merged_articles.append(row)
        for row in _kw_articles(session, q, category_slug, dt_from, dt_to, limit * 2):
            aid = int(row["article_id"])
            if aid in seen_a:
                continue
            seen_a.add(aid)
            row = dict(row)
            row["score"] = merge_hybrid_scores(1.0, None)
            merged_articles.append(row)
        merged_articles.sort(key=lambda x: float(x["score"]), reverse=True)
        merged_articles = merged_articles[:limit]

    return {
        "query": q,
        "mode": "hybrid",
        "results": {"topics": merged_topics, "articles": merged_articles},
    }
