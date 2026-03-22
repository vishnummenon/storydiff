"""Media leaderboard and publisher detail (live aggregation + optional aggregates table)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from storydiff.core_api.exceptions import CoreApiError
from storydiff.core_api.util import composite_rank_score, window_bounds_now
from storydiff.db.models import Article, ArticleAnalysis, Category, MediaOutlet, Topic


def _outlet_dict(m: MediaOutlet) -> dict:
    return {
        "id": int(m.id),
        "slug": m.slug,
        "name": m.name,
        "domain": m.domain,
    }


def _avg_metrics_from_rows(
    article_count: int,
    avg_cd,
    avg_fp,
    avg_sd,
    avg_nc,
    avg_rel,
) -> dict:
    cd = float(avg_cd) if avg_cd is not None else None
    fp = float(avg_fp) if avg_fp is not None else None
    sd = float(avg_sd) if avg_sd is not None else None
    nc = float(avg_nc) if avg_nc is not None else None
    rel = float(avg_rel) if avg_rel is not None else None
    comp = composite_rank_score(cd, rel)
    return {
        "article_count": int(article_count),
        "avg_consensus_distance": cd,
        "avg_framing_polarity": fp,
        "avg_source_diversity_score": sd,
        "avg_novel_claim_score": nc,
        "avg_reliability_score": rel,
        "composite_rank_score": comp,
    }


def _sort_key_item(item: dict, sort_by: str) -> float:
    m = item
    if sort_by == "composite_rank_score":
        v = m.get("composite_rank_score")
        return v if v is not None else -1.0
    if sort_by == "avg_consensus_distance":
        v = m.get("avg_consensus_distance")
        return v if v is not None else 1e9
    if sort_by == "avg_framing_polarity":
        v = m.get("avg_framing_polarity")
        return v if v is not None else -1e9
    if sort_by == "avg_novel_claim_score":
        v = m.get("avg_novel_claim_score")
        return v if v is not None else -1e9
    if sort_by == "avg_reliability_score":
        v = m.get("avg_reliability_score")
        return v if v is not None else -1.0
    v = m.get("composite_rank_score")
    return v if v is not None else -1.0


def _sort_reverse(sort_by: str) -> bool:
    """Whether to sort descending. Consensus distance: lower is better → ascending."""
    if sort_by == "avg_consensus_distance":
        return False
    return True


def get_media_leaderboard(
    session: Session,
    *,
    window_str: str,
    category_slug: str | None,
    limit: int,
    sort_by: str,
) -> dict:
    ws, we = window_bounds_now(window_str)

    if category_slug:
        cat = session.execute(select(Category).where(Category.slug == category_slug)).scalar_one_or_none()
        if cat is None:
            return {"window": window_str, "category": category_slug, "items": []}

    # Live aggregation over articles + analysis in the window (precomputed media_aggregates
    # rows use pipeline-specific window boundaries; rolling "now" windows match this path).
    stmt = (
        select(
            MediaOutlet.id,
            func.count(Article.id),
            func.avg(ArticleAnalysis.consensus_distance),
            func.avg(ArticleAnalysis.framing_polarity),
            func.avg(ArticleAnalysis.source_diversity_score),
            func.avg(ArticleAnalysis.novel_claim_score),
            func.avg(ArticleAnalysis.reliability_score),
        )
        .join(Article, Article.media_outlet_id == MediaOutlet.id)
        .outerjoin(ArticleAnalysis, ArticleAnalysis.article_id == Article.id)
        .where(Article.published_at >= ws, Article.published_at <= we)
        .group_by(MediaOutlet.id)
    )
    if category_slug:
        stmt = stmt.join(Category, Article.category_id == Category.id).where(Category.slug == category_slug)

    items: list[dict] = []
    for row in session.execute(stmt).all():
        oid, cnt, a1, a2, a3, a4, a5 = row
        mo = session.get(MediaOutlet, oid)
        if mo is None:
            continue
        metrics = _avg_metrics_from_rows(cnt, a1, a2, a3, a4, a5)
        items.append({"media_outlet": _outlet_dict(mo), **metrics})

    items.sort(key=lambda x: _sort_key_item(x, sort_by), reverse=_sort_reverse(sort_by))

    return {
        "window": window_str,
        "category": category_slug,
        "items": items[:limit],
    }


def get_media_detail(
    session: Session,
    media_id: int,
    *,
    window_str: str,
) -> dict:
    mo = session.get(MediaOutlet, media_id)
    if mo is None:
        raise CoreApiError("MEDIA_NOT_FOUND", "Media outlet not found", 404)

    ws, we = window_bounds_now(window_str)

    row = session.execute(
        select(
            func.count(Article.id),
            func.avg(ArticleAnalysis.consensus_distance),
            func.avg(ArticleAnalysis.framing_polarity),
            func.avg(ArticleAnalysis.source_diversity_score),
            func.avg(ArticleAnalysis.novel_claim_score),
            func.avg(ArticleAnalysis.reliability_score),
        )
        .select_from(Article)
        .outerjoin(ArticleAnalysis, ArticleAnalysis.article_id == Article.id)
        .where(
            Article.media_outlet_id == media_id,
            Article.published_at >= ws,
            Article.published_at <= we,
        )
    ).one()
    cnt, a1, a2, a3, a4, a5 = row
    overall = {
        "window": window_str,
        **_avg_metrics_from_rows(cnt or 0, a1, a2, a3, a4, a5),
    }

    # By category: group by category slug
    by_cat_rows = session.execute(
        select(
            Category.slug,
            func.count(Article.id),
            func.avg(ArticleAnalysis.consensus_distance),
            func.avg(ArticleAnalysis.framing_polarity),
            func.avg(ArticleAnalysis.source_diversity_score),
            func.avg(ArticleAnalysis.novel_claim_score),
            func.avg(ArticleAnalysis.reliability_score),
        )
        .select_from(Article)
        .join(Category, Article.category_id == Category.id)
        .outerjoin(ArticleAnalysis, ArticleAnalysis.article_id == Article.id)
        .where(
            Article.media_outlet_id == media_id,
            Article.published_at >= ws,
            Article.published_at <= we,
        )
        .group_by(Category.id, Category.slug)
    ).all()

    by_category: list[dict] = []
    for slug, c2, b1, b2, b3, b4, b5 in by_cat_rows:
        mets = _avg_metrics_from_rows(c2, b1, b2, b3, b4, b5)
        by_category.append({"category": slug, **mets})

    # Recent topics touched by this outlet in window
    topic_ids = (
        session.execute(
            select(Article.topic_id)
            .where(
                Article.media_outlet_id == media_id,
                Article.topic_id.isnot(None),
                Article.published_at >= ws,
                Article.published_at <= we,
            )
            .distinct()
            .limit(15)
        )
        .scalars()
        .all()
    )
    recent_topics: list[dict] = []
    for tid in topic_ids:
        if tid is None:
            continue
        t = session.get(Topic, tid)
        if t is None:
            continue
        recent_topics.append(
            {
                "topic_id": int(t.id),
                "title": t.current_title,
                "article_count": int(t.article_count),
                "last_seen_at": t.last_seen_at.isoformat() if t.last_seen_at else None,
            }
        )

    return {
        "media_outlet": _outlet_dict(mo),
        "overall_metrics": overall,
        "by_category": by_category,
        "recent_topics": recent_topics,
    }
