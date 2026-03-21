"""Topic detail and timeline."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from storydiff.core_api.exceptions import CoreApiError
from storydiff.core_api.util import polarity_labels_to_list
from storydiff.db.models import (
    Article,
    ArticleAnalysis,
    Category,
    MediaOutlet,
    Topic,
    TopicArticleLink,
    TopicVersion,
)


def _media_outlet_dict(m: MediaOutlet) -> dict:
    return {
        "id": int(m.id),
        "slug": m.slug,
        "name": m.name,
    }


def get_topic_detail(
    session: Session,
    topic_id: int,
    *,
    include_articles: bool,
    include_timeline_preview: bool,
    timeline_preview_limit: int = 5,
) -> dict:
    topic = session.get(Topic, topic_id)
    if topic is None:
        raise CoreApiError("TOPIC_NOT_FOUND", "Topic not found", 404)
    cat = session.get(Category, topic.category_id)
    if cat is None:
        raise CoreApiError("TOPIC_NOT_FOUND", "Topic category missing", 404)

    topic_block = {
        "id": int(topic.id),
        "category": {
            "id": int(cat.id),
            "slug": cat.slug,
            "name": cat.name,
        },
        "canonical_label": topic.canonical_label,
        "title": topic.current_title,
        "summary": topic.current_summary,
        "status": topic.status,
        "article_count": int(topic.article_count),
        "source_count": int(topic.source_count),
        "reliability_score": float(topic.current_reliability_score)
        if topic.current_reliability_score is not None
        else None,
        "first_seen_at": topic.first_seen_at.isoformat() if topic.first_seen_at else None,
        "last_seen_at": topic.last_seen_at.isoformat() if topic.last_seen_at else None,
        "current_consensus_version": int(topic.current_consensus_version),
    }

    data: dict = {"topic": topic_block}

    if include_articles:
        stmt = (
            select(Article, MediaOutlet, ArticleAnalysis, TopicArticleLink)
            .join(TopicArticleLink, TopicArticleLink.article_id == Article.id)
            .join(MediaOutlet, MediaOutlet.id == Article.media_outlet_id)
            .outerjoin(ArticleAnalysis, ArticleAnalysis.article_id == Article.id)
            .where(TopicArticleLink.topic_id == topic_id)
            .order_by(Article.published_at.desc())
        )
        rows = session.execute(stmt).all()
        articles_out: list[dict] = []
        for art, mo, aa, _link in rows:
            scores = {
                "consensus_distance": float(aa.consensus_distance)
                if aa is not None and aa.consensus_distance is not None
                else None,
                "framing_polarity": float(aa.framing_polarity)
                if aa is not None and aa.framing_polarity is not None
                else None,
                "source_diversity_score": float(aa.source_diversity_score)
                if aa is not None and aa.source_diversity_score is not None
                else None,
                "novel_claim_score": float(aa.novel_claim_score)
                if aa is not None and aa.novel_claim_score is not None
                else None,
                "reliability_score": float(aa.reliability_score)
                if aa is not None and aa.reliability_score is not None
                else None,
            }
            pol = polarity_labels_to_list(aa.polarity_labels_json) if aa is not None else []
            articles_out.append(
                {
                    "article_id": int(art.id),
                    "title": art.title,
                    "url": art.url,
                    "published_at": art.published_at.isoformat() if art.published_at else None,
                    "media_outlet": _media_outlet_dict(mo),
                    "summary": aa.summary if aa is not None else None,
                    "scores": scores,
                    "polarity_labels": pol,
                }
            )
        data["articles"] = articles_out
    else:
        data["articles"] = []

    if include_timeline_preview:
        prev_rows = (
            session.execute(
                select(TopicVersion)
                .where(TopicVersion.topic_id == topic_id)
                .order_by(TopicVersion.version_no.desc())
                .limit(timeline_preview_limit)
            )
            .scalars()
            .all()
        )
        prev_rows = list(reversed(prev_rows))
        data["timeline_preview"] = [
            {
                "version_no": int(v.version_no),
                "generated_at": v.generated_at.isoformat() if v.generated_at else None,
                "title": v.title,
            }
            for v in prev_rows
        ]
    else:
        data["timeline_preview"] = []

    return data


def get_topic_timeline(session: Session, topic_id: int) -> dict:
    topic = session.get(Topic, topic_id)
    if topic is None:
        raise CoreApiError("TOPIC_NOT_FOUND", "Topic not found", 404)
    versions = (
        session.execute(
            select(TopicVersion)
            .where(TopicVersion.topic_id == topic_id)
            .order_by(TopicVersion.version_no.asc())
        )
        .scalars()
        .all()
    )
    return {
        "topic_id": int(topic_id),
        "versions": [
            {
                "version_no": int(v.version_no),
                "title": v.title,
                "summary": v.summary,
                "reliability_score": float(v.reliability_score)
                if v.reliability_score is not None
                else None,
                "article_count": int(v.article_count),
                "source_count": int(v.source_count),
                "generated_at": v.generated_at.isoformat() if v.generated_at else None,
            }
            for v in versions
        ],
    }
