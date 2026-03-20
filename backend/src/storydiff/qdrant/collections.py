"""Idempotent Qdrant collection creation.

Point ID strategy (per phase-1 design): use the Postgres primary key as the Qdrant
point id for each collection — ``article_id`` for ``article_embeddings`` and
``topic_id`` for ``topic_embeddings``. That makes upserts by domain id idempotent
(replace the same point id on re-index).
"""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams

from storydiff.qdrant.settings import QdrantSettings, load_qdrant_settings


def _collection_names(client: QdrantClient) -> set[str]:
    return {c.name for c in client.get_collections().collections}


def ensure_collections(settings: QdrantSettings | None = None) -> None:
    """Create ``article_embeddings`` and ``topic_embeddings`` if they do not exist."""
    cfg = settings or load_qdrant_settings()
    client = QdrantClient(url=cfg.url, api_key=cfg.api_key)
    existing = _collection_names(client)
    params = VectorParams(size=cfg.vector_size, distance=cfg.distance)

    for name in (cfg.article_collection, cfg.topic_collection):
        if name in existing:
            continue
        client.create_collection(collection_name=name, vectors_config=params)
