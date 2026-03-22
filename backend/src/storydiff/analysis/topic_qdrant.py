"""Topic embedding upsert and candidate search (``topic_embeddings`` collection)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from storydiff.db.models import Topic
from storydiff.qdrant.payloads import TOPIC_PAYLOAD_FIELDS
from storydiff.qdrant.settings import QdrantSettings, load_qdrant_settings


def _as_vector(v: Any) -> list[float] | None:
    if v is None:
        return None
    if isinstance(v, dict):
        if not v:
            return None
        return _as_vector(next(iter(v.values())))
    if isinstance(v, (list, tuple)):
        return [float(x) for x in v]
    return None


def _iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_topic_payload(topic: Topic) -> dict:
    return {
        "topic_id": int(topic.id),
        "category_id": int(topic.category_id),
        "status": topic.status,
        "last_seen_at": _iso_z(topic.last_seen_at),
        "article_count": int(topic.article_count),
        "source_count": int(topic.source_count),
        "consensus_version": int(topic.current_consensus_version),
    }


def validate_topic_payload(payload: dict) -> None:
    if set(payload.keys()) != TOPIC_PAYLOAD_FIELDS:
        raise ValueError(
            f"Topic payload keys {set(payload.keys())!r} must match {TOPIC_PAYLOAD_FIELDS!r}"
        )


def upsert_topic_embedding(
    client: QdrantClient,
    collection: str,
    topic: Topic,
    vector: list[float],
    expected_dim: int,
) -> None:
    if len(vector) != expected_dim:
        raise ValueError(
            f"Topic vector length {len(vector)} does not match expected_dim {expected_dim}"
        )
    payload = build_topic_payload(topic)
    validate_topic_payload(payload)
    client.upsert(
        collection_name=collection,
        points=[PointStruct(id=int(topic.id), vector=vector, payload=payload)],
    )


def search_topic_candidates(
    client: QdrantClient,
    collection: str,
    query_vector: list[float],
    *,
    limit: int,
) -> list[tuple[int, float]]:
    """Return ``(topic_id, score)`` from Qdrant similarity search (score = similarity)."""
    hits = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    out: list[tuple[int, float]] = []
    for h in hits.points:
        tid = h.payload.get("topic_id") if h.payload else None
        if tid is None:
            continue
        out.append((int(tid), float(h.score)))
    return out


def retrieve_topic_vector(
    client: QdrantClient,
    collection: str,
    topic_id: int,
) -> list[float] | None:
    pts = client.retrieve(
        collection_name=collection,
        ids=[topic_id],
        with_vectors=True,
    )
    if not pts:
        return None
    return _as_vector(pts[0].vector)


def retrieve_article_vector(
    client: QdrantClient,
    collection: str,
    article_id: int,
) -> list[float] | None:
    pts = client.retrieve(
        collection_name=collection,
        ids=[article_id],
        with_vectors=True,
    )
    if not pts:
        return None
    return _as_vector(pts[0].vector)


def upsert_topic_embedding_with_settings(
    topic: Topic,
    vector: list[float],
    settings: QdrantSettings | None = None,
) -> None:
    cfg = settings or load_qdrant_settings()
    client = QdrantClient(url=cfg.url, api_key=cfg.api_key)
    upsert_topic_embedding(client, cfg.topic_collection, topic, vector, cfg.vector_size)
