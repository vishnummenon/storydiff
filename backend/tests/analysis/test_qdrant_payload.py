"""Qdrant article payload shape and dimension checks."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from storydiff.analysis.qdrant_write import build_article_payload, validate_payload_keys
from storydiff.db.models import Article


def _article(**kwargs: object) -> Article:
    defaults = dict(
        id=1,
        media_outlet_id=2,
        url="https://example.com/a",
        canonical_url="https://example.com/a",
        title="T",
        language="en",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        article_fingerprint="fp",
        dedupe_key="k",
        processing_status="pending",
    )
    defaults.update(kwargs)
    return Article(**defaults)  # type: ignore[arg-type]


def test_build_article_payload_keys_match_spec() -> None:
    a = _article(category_id=3, topic_id=None)
    p = build_article_payload(a)
    validate_payload_keys(p)
    assert p["article_id"] == 1
    assert p["category_id"] == 3
    assert p["topic_id"] is None


def test_upsert_rejects_wrong_vector_length() -> None:
    from qdrant_client import QdrantClient

    from storydiff.analysis.qdrant_write import upsert_article_embedding

    a = _article()
    with pytest.raises(ValueError, match="Vector length"):
        upsert_article_embedding(
            QdrantClient(url="http://localhost:6333"),
            "article_embeddings",
            a,
            [0.0] * 5,
            expected_dim=384,
        )
