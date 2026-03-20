"""Upsert article vectors into Qdrant (``article_embeddings``)."""

from __future__ import annotations

from datetime import datetime, timezone

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from storydiff.db.models import Article
from storydiff.qdrant.payloads import ARTICLE_PAYLOAD_FIELDS
from storydiff.qdrant.settings import QdrantSettings, load_qdrant_settings


def _iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_article_payload(article: Article) -> dict:
    """Payload keys per architecture / qdrant-embeddings spec."""
    return {
        "article_id": int(article.id),
        "media_outlet_id": int(article.media_outlet_id),
        "category_id": int(article.category_id) if article.category_id is not None else None,
        "topic_id": int(article.topic_id) if article.topic_id is not None else None,
        "published_at": _iso_z(article.published_at),
        "language": article.language,
        "title": article.title,
        "url": article.url,
    }


def validate_payload_keys(payload: dict) -> None:
    if set(payload.keys()) != ARTICLE_PAYLOAD_FIELDS:
        raise ValueError(
            f"Article payload keys {set(payload.keys())!r} must match {ARTICLE_PAYLOAD_FIELDS!r}"
        )


def upsert_article_embedding(
    client: QdrantClient,
    collection: str,
    article: Article,
    vector: list[float],
    expected_dim: int,
) -> None:
    if len(vector) != expected_dim:
        raise ValueError(
            f"Vector length {len(vector)} does not match EMBEDDING_VECTOR_SIZE {expected_dim}"
        )
    payload = build_article_payload(article)
    validate_payload_keys(payload)
    client.upsert(
        collection_name=collection,
        points=[
            PointStruct(
                id=int(article.id),
                vector=vector,
                payload=payload,
            )
        ],
    )


def upsert_article_embedding_with_settings(
    article: Article,
    vector: list[float],
    settings: QdrantSettings | None = None,
) -> None:
    cfg = settings or load_qdrant_settings()
    client = QdrantClient(url=cfg.url, api_key=cfg.api_key)
    upsert_article_embedding(
        client,
        cfg.article_collection,
        article,
        vector,
        cfg.vector_size,
    )
