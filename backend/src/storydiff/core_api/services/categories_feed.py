"""Categories list and feed (category → topic tiles)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from storydiff.db.models import Category, Topic


def list_categories_data(session: Session) -> dict:
    rows = (
        session.execute(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.display_order, Category.id)
        )
        .scalars()
        .all()
    )
    return {
        "categories": [
            {
                "id": int(r.id),
                "slug": r.slug,
                "name": r.name,
                "display_order": int(r.display_order),
            }
            for r in rows
        ]
    }


def _topic_tile(t: Topic) -> dict:
    return {
        "id": int(t.id),
        "title": t.current_title,
        "summary": t.current_summary,
        "article_count": int(t.article_count),
        "source_count": int(t.source_count),
        "reliability_score": float(t.current_reliability_score)
        if t.current_reliability_score is not None
        else None,
        "last_updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def get_feed_data(
    session: Session,
    *,
    category_slug: str | None,
    limit_per_category: int,
    include_empty_categories: bool,
) -> dict:
    cq = select(Category).where(Category.is_active.is_(True)).order_by(
        Category.display_order, Category.id
    )
    if category_slug:
        cq = cq.where(Category.slug == category_slug)
    categories = session.execute(cq).scalars().all()

    out: list[dict] = []
    for c in categories:
        tq = (
            select(Topic)
            .where(Topic.category_id == c.id, Topic.status == "active")
            .order_by(Topic.last_seen_at.desc())
            .limit(limit_per_category)
        )
        topics = session.execute(tq).scalars().all()
        if not topics and not include_empty_categories:
            continue
        out.append(
            {
                "id": int(c.id),
                "slug": c.slug,
                "name": c.name,
                "topics": [_topic_tile(t) for t in topics],
            }
        )
    return {"categories": out}
