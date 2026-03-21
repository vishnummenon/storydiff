"""API tests for Core Read GET endpoints."""

from __future__ import annotations

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
