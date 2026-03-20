"""Payload field names for Qdrant collections (architecture/db_schema.md §5.1–5.2).

Values written to Qdrant should use these keys. Types: integers, strings, ISO 8601
strings for timestamps — see architecture examples.
"""

from __future__ import annotations

from typing import Final

# §5.1 article_embeddings
ARTICLE_PAYLOAD_FIELDS: Final[frozenset[str]] = frozenset(
    (
        "article_id",
        "media_outlet_id",
        "category_id",
        "topic_id",
        "published_at",
        "language",
        "title",
        "url",
    )
)

# §5.2 topic_embeddings
TOPIC_PAYLOAD_FIELDS: Final[frozenset[str]] = frozenset(
    (
        "topic_id",
        "category_id",
        "status",
        "last_seen_at",
        "article_count",
        "source_count",
        "consensus_version",
    )
)
