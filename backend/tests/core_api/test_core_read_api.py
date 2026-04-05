"""API tests for Core Read GET endpoints."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

def test_categories_empty(client, db_session, cleanup_core_tables):
    r = client.get("/api/v1/categories")
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    assert body["data"]["categories"] == []


def test_categories_and_feed(sample_feed_data, client):
    r = client.get("/api/v1/categories")
    assert r.status_code == 200
    cats = r.json()["data"]["categories"]
    assert len(cats) == 1
    assert cats[0]["slug"] == "geopolitics"

    r = client.get("/api/v1/feed")
    assert r.status_code == 200
    data = r.json()["data"]["categories"]
    assert len(data) == 1
    assert data[0]["topics"][0]["title"] == "Iran tensions"


def test_topic_not_found(client, db_session, cleanup_core_tables):
    r = client.get("/api/v1/topics/99999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "TOPIC_NOT_FOUND"


def test_search_keyword_no_embedding_config(client, db_session, cleanup_core_tables):
    """Keyword search must not require embedding service."""
    r = client.get("/api/v1/search", params={"q": "iran", "mode": "keyword"})
    assert r.status_code == 200
    assert r.json()["error"] is None
    assert r.json()["data"]["mode"] == "keyword"


def test_media_not_found(client, db_session, cleanup_core_tables):
    r = client.get("/api/v1/media/99999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "MEDIA_NOT_FOUND"


def test_media_leaderboard_empty_window(client, db_session, cleanup_core_tables):
    r = client.get("/api/v1/media")
    assert r.status_code == 200
    assert r.json()["data"]["items"] == []


# ---------------------------------------------------------------------------
# Search tests — FTS keyword, filters, and error paths
# ---------------------------------------------------------------------------

def _make_article(db_session, *, media_outlet_id: int, category_id: int, title: str, published_at: datetime) -> object:
    """Insert a minimal article row and return it."""
    from storydiff.db.models import Article

    key = hashlib.sha256(title.encode()).hexdigest()[:64]
    art = Article(
        media_outlet_id=media_outlet_id,
        url=f"https://example.com/{key}",
        canonical_url=f"https://example.com/{key}",
        title=title,
        language="en",
        published_at=published_at,
        article_fingerprint=key,
        dedupe_key=key,
        processing_status="analyzed",
        category_id=category_id,
    )
    db_session.add(art)
    db_session.commit()
    db_session.refresh(art)
    return art


def test_search_keyword_returns_topic(sample_feed_data, client):
    """A word from the topic title should appear in results.topics."""
    r = client.get("/api/v1/search", params={"q": "tensions", "mode": "keyword"})
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    topics = body["data"]["results"]["topics"]
    assert any(t["topic_id"] == sample_feed_data["topic"].id for t in topics)


def test_search_keyword_returns_article(sample_feed_data, db_session, client):
    """A word from the article title should appear in results.articles."""
    from storydiff.db.models import MediaOutlet

    mo = MediaOutlet(slug="test-outlet", name="Test Outlet", domain="testoutlet.example.com")
    db_session.add(mo)
    db_session.flush()
    published = datetime(2026, 3, 20, 8, 0, 0, tzinfo=timezone.utc)
    art = _make_article(
        db_session,
        media_outlet_id=mo.id,
        category_id=sample_feed_data["category"].id,
        title="Sanctions escalate overnight",
        published_at=published,
    )
    r = client.get("/api/v1/search", params={"q": "sanctions", "mode": "keyword"})
    assert r.status_code == 200
    articles = r.json()["data"]["results"]["articles"]
    assert any(a["article_id"] == art.id for a in articles)


def test_search_keyword_category_filter(sample_feed_data, client):
    """A non-matching category slug should exclude the topic from results."""
    r = client.get(
        "/api/v1/search",
        params={"q": "tensions", "mode": "keyword", "category": "nonexistent-slug"},
    )
    assert r.status_code == 200
    topics = r.json()["data"]["results"]["topics"]
    assert topics == []


def test_search_keyword_date_range_filter(sample_feed_data, db_session, client):
    """An article outside the from/to window should be excluded."""
    from storydiff.db.models import MediaOutlet

    mo = MediaOutlet(slug="date-outlet", name="Date Outlet", domain="dateoutlet.example.com")
    db_session.add(mo)
    db_session.flush()
    published = datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
    _make_article(
        db_session,
        media_outlet_id=mo.id,
        category_id=sample_feed_data["category"].id,
        title="Nuclear talks stall in Vienna",
        published_at=published,
    )
    # Query with a date range that excludes Jan 15
    r = client.get(
        "/api/v1/search",
        params={
            "q": "nuclear",
            "mode": "keyword",
            "from": "2026-02-01T00:00:00Z",
            "to": "2026-03-01T00:00:00Z",
        },
    )
    assert r.status_code == 200
    articles = r.json()["data"]["results"]["articles"]
    assert articles == []


def test_search_invalid_mode_returns_422(client, db_session, cleanup_core_tables):
    """Unsupported mode value must return 422 VALIDATION_ERROR."""
    r = client.get("/api/v1/search", params={"q": "test", "mode": "garbage"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_search_semantic_without_qdrant_returns_503(client, db_session, cleanup_core_tables):
    """Semantic search without Qdrant configured must return 503 SEARCH_UNAVAILABLE."""
    from storydiff.core_api.deps import get_qdrant_client_optional
    from storydiff.main import app

    app.dependency_overrides[get_qdrant_client_optional] = lambda: None
    try:
        r = client.get("/api/v1/search", params={"q": "test", "mode": "semantic"})
    finally:
        app.dependency_overrides.pop(get_qdrant_client_optional, None)

    assert r.status_code == 503
    assert r.json()["error"]["code"] == "SEARCH_UNAVAILABLE"
