"""FastAPI routes for Core Read API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from storydiff.core_api.deps import get_embedding_service, get_qdrant_client_optional
from storydiff.core_api.exceptions import CoreApiError
from storydiff.core_api.services.categories_feed import get_feed_data, list_categories_data
from storydiff.core_api.services.media_service import get_media_detail, get_media_leaderboard
from storydiff.core_api.services.search_service import run_search
from storydiff.core_api.services.topics_service import get_topic_detail, get_topic_timeline
from storydiff.db.session import get_db
from storydiff.ingestion.envelope import success_response

router = APIRouter(tags=["core-read"])


def _parse_iso_dt(raw: str | None) -> datetime | None:
    if raw is None or raw.strip() == "":
        return None
    s = raw.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(s)


@router.get("/categories")
def get_categories(session: Session = Depends(get_db)):
    return success_response(list_categories_data(session))


@router.get("/feed")
def get_feed(
    session: Session = Depends(get_db),
    category: str | None = Query(None),
    limit_per_category: int = Query(10, ge=1, le=100),
    include_empty_categories: bool = Query(False),
):
    data = get_feed_data(
        session,
        category_slug=category,
        limit_per_category=limit_per_category,
        include_empty_categories=include_empty_categories,
    )
    return success_response(data)


@router.get("/topics/{topic_id}")
def get_topic(
    topic_id: int,
    session: Session = Depends(get_db),
    include_articles: bool = Query(True),
    include_timeline_preview: bool = Query(True),
):
    data = get_topic_detail(
        session,
        topic_id,
        include_articles=include_articles,
        include_timeline_preview=include_timeline_preview,
    )
    return success_response(data)


@router.get("/topics/{topic_id}/timeline")
def get_timeline(topic_id: int, session: Session = Depends(get_db)):
    return success_response(get_topic_timeline(session, topic_id))


_MEDIA_SORT = frozenset(
    {
        "composite_rank_score",
        "avg_consensus_distance",
        "avg_framing_polarity",
        "avg_novel_claim_score",
        "avg_reliability_score",
    }
)


@router.get("/media")
def list_media(
    session: Session = Depends(get_db),
    category: str | None = Query(None),
    window: str = Query("30d"),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query(
        "composite_rank_score",
        description="Leaderboard ordering (see architecture/api_contract.md §8.5).",
    ),
):
    if sort_by not in _MEDIA_SORT:
        raise CoreApiError("VALIDATION_ERROR", f"sort_by must be one of {sorted(_MEDIA_SORT)}", 422)
    data = get_media_leaderboard(
        session,
        window_str=window,
        category_slug=category,
        limit=limit,
        sort_by=sort_by,
    )
    return success_response(data)


@router.get("/media/{media_id}")
def media_detail(
    media_id: int,
    session: Session = Depends(get_db),
    window: str = Query("30d"),
):
    return success_response(get_media_detail(session, media_id, window_str=window))


@router.get("/search")
def search(
    session: Session = Depends(get_db),
    q: str = Query(..., min_length=1),
    mode: str = Query("keyword", description="keyword | semantic | hybrid"),
    result_type: str = Query("all", alias="type"),
    category: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    qclient: QdrantClient | None = Depends(get_qdrant_client_optional),
):
    if mode not in ("keyword", "semantic", "hybrid"):
        raise CoreApiError("VALIDATION_ERROR", "mode must be keyword, semantic, or hybrid", 422)
    if result_type not in ("topics", "articles", "all"):
        raise CoreApiError("VALIDATION_ERROR", "type must be topics, articles, or all", 422)
    embedding = get_embedding_service() if mode in ("semantic", "hybrid") else None
    try:
        inner = run_search(
            session,
            q=q,
            mode=mode,
            result_type=result_type,
            category_slug=category,
            dt_from=_parse_iso_dt(from_),
            dt_to=_parse_iso_dt(to),
            limit=limit,
            embedding=embedding,
            qclient=qclient,
        )
    except RuntimeError as e:
        raise CoreApiError("SEARCH_UNAVAILABLE", str(e), 503) from e
    return success_response(inner)

