"""FastAPI dependencies for Core Read API."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient

from storydiff.analysis.embeddings import EmbeddingService

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def get_embedding_service() -> EmbeddingService:
    """Dense embedding for semantic search; dimension from ``EMBEDDING_VECTOR_SIZE``."""
    load_dotenv(_BACKEND_ROOT / ".env")
    dim_raw = os.environ.get("EMBEDDING_VECTOR_SIZE", "").strip()
    if not dim_raw:
        raise RuntimeError("EMBEDDING_VECTOR_SIZE must be set for Core API search")
    return EmbeddingService(expected_dim=int(dim_raw))


def get_qdrant_client_optional() -> QdrantClient | None:
    """Returns ``None`` if Qdrant is not configured (keyword search still works)."""
    try:
        from storydiff.qdrant.settings import load_qdrant_settings

        cfg = load_qdrant_settings()
    except RuntimeError:
        return None
    return QdrantClient(url=cfg.url, api_key=cfg.api_key)
