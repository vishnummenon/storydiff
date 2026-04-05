"""Integration test: RSS feed XML → ingest API submission."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from storydiff.rss.config import FeedConfig
from storydiff.rss.extractor import TextExtractor
from storydiff.rss.fetcher import submit_articles

SAMPLE_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article One</title>
      <link>https://example.com/article-1</link>
      <description>Summary of article one</description>
      <pubDate>Sat, 05 Apr 2026 08:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Article Two</title>
      <link>https://example.com/article-2</link>
      <description>Summary of article two</description>
      <pubDate>Sat, 05 Apr 2026 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


@pytest.fixture()
def feed():
    return FeedConfig(url="https://example.com/rss", outlet_slug="example", category="world")


def test_end_to_end_with_mocked_http(feed):
    """Verify the full flow: RSS parsing → text extraction → ingest API call."""
    ingest_calls = []

    def mock_transport(request: httpx.Request) -> httpx.Response:
        if "/api/v1/ingest" in str(request.url):
            ingest_calls.append(request)
            return httpx.Response(
                200,
                json={
                    "data": {
                        "article_id": len(ingest_calls),
                        "dedupe_status": "inserted",
                        "processing_status": "pending",
                    },
                    "meta": {},
                    "error": None,
                },
            )
        return httpx.Response(404)

    extractor = TextExtractor(delay_seconds=0)

    with (
        patch("storydiff.rss.fetcher.feedparser.parse") as mock_parse,
        patch.object(extractor, "extract", return_value=("Full text content", "https://example.com/article-1")),
        patch("storydiff.rss.fetcher.httpx.Client") as mock_client_cls,
    ):
        # Set up feedparser mock
        mock_parse.return_value.bozo = False
        mock_parse.return_value.entries = [
            {
                "title": "Article One",
                "link": "https://example.com/article-1",
                "summary": "Summary of article one",
                "published_parsed": (2026, 4, 5, 8, 0, 0, 5, 95, 0),
            },
            {
                "title": "Article Two",
                "link": "https://example.com/article-2",
                "summary": "Summary of article two",
                "published_parsed": (2026, 4, 5, 9, 0, 0, 5, 95, 0),
            },
        ]

        # Set up httpx mock
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.post.return_value = httpx.Response(
            200,
            json={
                "data": {
                    "article_id": 1,
                    "dedupe_status": "inserted",
                    "processing_status": "pending",
                },
                "meta": {},
                "error": None,
            },
        )

        stats = submit_articles([feed], extractor, "http://localhost:8000")

    assert stats["submitted"] == 2
    assert stats["errors"] == 0
    assert mock_client.post.call_count == 2

    # Verify payload structure of first call
    first_call_payload = mock_client.post.call_args_list[0][1]["json"]
    assert first_call_payload["title"] == "Article One"
    assert first_call_payload["url"] == "https://example.com/article-1"
    assert first_call_payload["raw_text"] == "Full text content"
    assert first_call_payload["media_outlet_slug"] == "example"


def test_duplicate_counted_correctly(feed):
    """Verify duplicate_ignored responses are counted separately."""
    extractor = TextExtractor(delay_seconds=0)

    with (
        patch("storydiff.rss.fetcher.feedparser.parse") as mock_parse,
        patch.object(extractor, "extract", return_value=(None, "https://example.com/resolved")),
        patch("storydiff.rss.fetcher.httpx.Client") as mock_client_cls,
    ):
        mock_parse.return_value.bozo = False
        mock_parse.return_value.entries = [
            {"title": "Dup Article", "link": "https://example.com/dup"},
        ]

        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.post.return_value = httpx.Response(
            200,
            json={
                "data": {
                    "article_id": 99,
                    "dedupe_status": "duplicate_ignored",
                    "processing_status": "pending",
                },
                "meta": {},
                "error": None,
            },
        )

        stats = submit_articles([feed], extractor, "http://localhost:8000")

    assert stats["duplicates"] == 1
    assert stats["submitted"] == 0


def test_api_error_counted_and_continues(feed):
    """Verify API errors don't halt processing."""
    extractor = TextExtractor(delay_seconds=0)

    with (
        patch("storydiff.rss.fetcher.feedparser.parse") as mock_parse,
        patch.object(extractor, "extract", return_value=(None, "https://example.com/resolved")),
        patch("storydiff.rss.fetcher.httpx.Client") as mock_client_cls,
    ):
        mock_parse.return_value.bozo = False
        mock_parse.return_value.entries = [
            {"title": "Bad Article", "link": "https://example.com/bad"},
            {"title": "Good Article", "link": "https://example.com/good"},
        ]

        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.post.side_effect = [
            httpx.Response(422, json={"error": {"code": "validation", "message": "bad"}}),
            httpx.Response(
                200,
                json={
                    "data": {"article_id": 2, "dedupe_status": "inserted", "processing_status": "pending"},
                    "meta": {},
                    "error": None,
                },
            ),
        ]

        stats = submit_articles([feed], extractor, "http://localhost:8000")

    assert stats["errors"] == 1
    assert stats["submitted"] == 1
