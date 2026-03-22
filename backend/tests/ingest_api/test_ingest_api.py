"""API tests for POST /api/v1/ingest."""

from __future__ import annotations

import pytest

from storydiff.ingestion.deps import get_publisher
from storydiff.ingestion.publisher import NoopPublisher


@pytest.fixture(autouse=True)
def noop_publisher():
    """Avoid real SQS during API tests."""
    from storydiff.main import app

    app.dependency_overrides[get_publisher] = lambda: NoopPublisher()
    yield
    app.dependency_overrides.pop(get_publisher, None)


def _valid_body(**overrides):
    base = {
        "source_article_id": "abc-123",
        "media_outlet_slug": "reuters",
        "url": "https://example.com/news/abc-123",
        "canonical_url": "https://example.com/news/abc-123",
        "title": "Iran warns of retaliation after strike",
        "raw_text": "body",
        "snippet": "short",
        "language": "en",
        "published_at": "2026-03-20T08:00:00Z",
        "source_category": "world",
    }
    base.update(overrides)
    return base


def test_ingest_validation_error(client, media_outlet):
    b = _valid_body()
    del b["title"]
    r = client.post("/api/v1/ingest", json=b)
    assert r.status_code == 422
    body = r.json()
    assert body["data"] is None
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_ingest_success_inserted(client, media_outlet):
    r = client.post("/api/v1/ingest", json=_valid_body())
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    assert body["data"]["dedupe_status"] == "inserted"
    assert body["data"]["processing_status"] == "pending"
    assert body["data"]["article_id"] >= 1


def test_ingest_duplicate_ignored(client, media_outlet):
    client.post("/api/v1/ingest", json=_valid_body())
    r = client.post("/api/v1/ingest", json=_valid_body())
    assert r.status_code == 200
    assert r.json()["data"]["dedupe_status"] == "duplicate_ignored"


def test_ingest_updated(client, media_outlet):
    client.post("/api/v1/ingest", json=_valid_body())
    r = client.post("/api/v1/ingest", json=_valid_body(title="New title"))
    assert r.status_code == 200
    assert r.json()["data"]["dedupe_status"] == "updated"


def test_media_outlet_not_found(client, media_outlet):
    r = client.post("/api/v1/ingest", json=_valid_body(media_outlet_slug="unknown"))
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "MEDIA_OUTLET_NOT_FOUND"
