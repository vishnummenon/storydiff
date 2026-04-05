"""Tests for RSS entry mapping and outlet resolution."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from storydiff.rss.config import FeedConfig
from storydiff.rss.fetcher import (
    _entry_to_payload,
    _parse_published,
    _resolve_outlet_slug,
    _slugify,
)


@pytest.fixture()
def basic_feed():
    return FeedConfig(url="https://example.com/rss", outlet_slug="example", category="world")


@pytest.fixture()
def gnews_feed():
    return FeedConfig(
        url="https://news.google.com/rss/search?q=test",
        outlet_slug="google-news",
        category="world",
        source_map={"Reuters": "reuters", "BBC News": "bbc"},
    )


class TestSlugify:
    def test_simple(self):
        assert _slugify("Reuters") == "reuters"

    def test_spaces_and_special_chars(self):
        assert _slugify("The Kerala Times") == "the-kerala-times"

    def test_leading_trailing(self):
        assert _slugify("  CNN  ") == "cnn"


class TestParsePublished:
    def test_with_published_parsed(self):
        entry = MagicMock()
        entry.published_parsed = (2026, 4, 5, 8, 0, 0, 5, 95, 0)
        entry.updated_parsed = None
        dt = _parse_published(entry)
        assert dt.year == 2026
        assert dt.month == 4
        assert dt.day == 5

    def test_fallback_to_updated(self):
        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = (2026, 3, 1, 12, 0, 0, 0, 60, 0)
        dt = _parse_published(entry)
        assert dt.year == 2026
        assert dt.month == 3

    def test_fallback_to_now(self):
        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = None
        dt = _parse_published(entry)
        assert (datetime.now(UTC) - dt).total_seconds() < 5


class TestResolveOutletSlug:
    def test_no_source_tag_uses_feed_slug(self, basic_feed):
        entry = {"title": "Test", "link": "https://example.com/1"}
        assert _resolve_outlet_slug(entry, basic_feed) == "example"

    def test_known_source_maps(self, gnews_feed):
        entry = {"title": "Test", "link": "https://example.com/1", "source": {"title": "Reuters"}}
        assert _resolve_outlet_slug(entry, gnews_feed) == "reuters"

    def test_unknown_source_slugified(self, gnews_feed):
        entry = {"title": "Test", "link": "https://example.com/1", "source": {"title": "The Kerala Times"}}
        assert _resolve_outlet_slug(entry, gnews_feed) == "the-kerala-times"

    def test_empty_source_uses_feed_slug(self, gnews_feed):
        entry = {"title": "Test", "link": "https://example.com/1", "source": {"title": ""}}
        assert _resolve_outlet_slug(entry, gnews_feed) == "google-news"


class TestEntryToPayload:
    def test_standard_mapping(self, basic_feed):
        entry = {
            "title": "Test Article",
            "link": "https://example.com/article/1",
            "summary": "A short summary",
        }

        payload = _entry_to_payload(entry, basic_feed, "Full article text here")
        assert payload["title"] == "Test Article"
        assert payload["url"] == "https://example.com/article/1"
        assert payload["canonical_url"] == "https://example.com/article/1"
        assert payload["raw_text"] == "Full article text here"
        assert payload["snippet"] == "A short summary"
        assert payload["media_outlet_slug"] == "example"
        assert payload["source_category"] == "world"

    def test_missing_raw_text(self, basic_feed):
        entry = {"title": "No Text", "link": "https://example.com/2"}

        payload = _entry_to_payload(entry, basic_feed, None)
        assert payload["raw_text"] is None
