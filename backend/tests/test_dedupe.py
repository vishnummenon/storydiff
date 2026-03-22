"""Unit tests for dedupe key helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from storydiff.ingestion.dedupe import (
    compute_dedupe_key,
    hour_bucket_utc,
    normalize_canonical_url,
    normalize_title,
)


def test_normalize_title_collapses_whitespace():
    assert normalize_title("  hello   world  ") == "hello world"


def test_normalize_canonical_url_strips_fragment_and_lowercases_host():
    u = normalize_canonical_url("HTTPS://Example.COM/path/to/?q=1#frag")
    assert "#" not in u
    assert "example.com" in u


def test_hour_bucket_utc():
    dt = datetime(2026, 3, 20, 8, 30, tzinfo=timezone.utc)
    assert hour_bucket_utc(dt) == "2026-03-20-08"


def test_compute_dedupe_key_tier1_canonical():
    pub = datetime(2026, 3, 20, 8, 0, tzinfo=timezone.utc)
    a = compute_dedupe_key(
        canonical_url="https://Example.COM/a/",
        source_article_id=None,
        media_outlet_id=1,
        title="ignored when canonical set",
        published_at=pub,
    )
    b = compute_dedupe_key(
        canonical_url="https://example.com/a",
        source_article_id=None,
        media_outlet_id=1,
        title="different",
        published_at=pub,
    )
    assert a == b
    assert len(a) == 64


def test_compute_dedupe_key_tier2_source_article_id():
    pub = datetime(2026, 3, 20, 8, 0, tzinfo=timezone.utc)
    k = compute_dedupe_key(
        canonical_url=None,
        source_article_id="src-1",
        media_outlet_id=7,
        title="t",
        published_at=pub,
    )
    assert len(k) == 64


def test_compute_dedupe_key_tier3_fallback():
    pub = datetime(2026, 3, 20, 8, 0, tzinfo=timezone.utc)
    k1 = compute_dedupe_key(
        canonical_url=None,
        source_article_id=None,
        media_outlet_id=3,
        title="Hello world",
        published_at=pub,
    )
    k2 = compute_dedupe_key(
        canonical_url=None,
        source_article_id=None,
        media_outlet_id=3,
        title="Hello  world",
        published_at=pub,
    )
    assert k1 == k2
