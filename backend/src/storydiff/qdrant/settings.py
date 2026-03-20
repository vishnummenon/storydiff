"""Qdrant configuration from environment.

Vector size and distance MUST match the embedding model used for articles and topics.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client.models import Distance

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _parse_distance(raw: str) -> Distance:
    key = raw.strip().upper()
    if key == "COSINE":
        return Distance.COSINE
    if key == "DOT":
        return Distance.DOT
    if key == "EUCLID" or key == "EUCLIDEAN":
        return Distance.EUCLID
    raise ValueError(
        f"Unsupported QDRANT_DISTANCE_METRIC={raw!r}; use COSINE, DOT, or EUCLID"
    )


@dataclass(frozen=True)
class QdrantSettings:
    url: str
    api_key: str | None
    article_collection: str
    topic_collection: str
    vector_size: int
    distance: Distance


def load_qdrant_settings() -> QdrantSettings:
    load_dotenv(_BACKEND_ROOT / ".env")
    url = os.environ.get("QDRANT_URL", "").strip()
    if not url:
        raise RuntimeError("QDRANT_URL must be set")

    api_key = os.environ.get("QDRANT_API_KEY", "").strip() or None
    article_collection = os.environ.get(
        "QDRANT_ARTICLE_EMBEDDINGS_COLLECTION", "article_embeddings"
    ).strip()
    topic_collection = os.environ.get(
        "QDRANT_TOPIC_EMBEDDINGS_COLLECTION", "topic_embeddings"
    ).strip()
    size_raw = os.environ.get("EMBEDDING_VECTOR_SIZE", "").strip()
    if not size_raw:
        raise RuntimeError(
            "EMBEDDING_VECTOR_SIZE must be set to the embedding model output dimension "
            "(same for article and topic vectors per architecture)."
        )
    vector_size = int(size_raw)
    dist_raw = os.environ.get("QDRANT_DISTANCE_METRIC", "COSINE").strip()
    distance = _parse_distance(dist_raw)

    return QdrantSettings(
        url=url,
        api_key=api_key,
        article_collection=article_collection,
        topic_collection=topic_collection,
        vector_size=vector_size,
        distance=distance,
    )
