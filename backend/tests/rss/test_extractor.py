"""Tests for full-text extraction."""

from __future__ import annotations

from unittest.mock import patch

from storydiff.rss.extractor import TextExtractor


class TestTextExtractor:
    def test_successful_extraction(self):
        extractor = TextExtractor(delay_seconds=0)
        with (
            patch("storydiff.rss.extractor.resolve_url", return_value="https://example.com/article"),
            patch("storydiff.rss.extractor.trafilatura.fetch_url", return_value="<html>content</html>"),
            patch("storydiff.rss.extractor.trafilatura.extract", return_value="Extracted article text"),
        ):
            text, url = extractor.extract("https://example.com/article")
        assert text == "Extracted article text"
        assert url == "https://example.com/article"

    def test_download_failure_returns_none(self):
        extractor = TextExtractor(delay_seconds=0)
        with (
            patch("storydiff.rss.extractor.resolve_url", return_value="https://example.com/bad"),
            patch("storydiff.rss.extractor.trafilatura.fetch_url", return_value=None),
        ):
            text, url = extractor.extract("https://example.com/bad")
        assert text is None
        assert url == "https://example.com/bad"

    def test_extraction_failure_returns_none(self):
        extractor = TextExtractor(delay_seconds=0)
        with (
            patch("storydiff.rss.extractor.resolve_url", return_value="https://example.com/empty"),
            patch("storydiff.rss.extractor.trafilatura.fetch_url", return_value="<html></html>"),
            patch("storydiff.rss.extractor.trafilatura.extract", return_value=None),
        ):
            text, url = extractor.extract("https://example.com/empty")
        assert text is None

    def test_exception_returns_none(self):
        extractor = TextExtractor(delay_seconds=0)
        with (
            patch("storydiff.rss.extractor.resolve_url", return_value="https://example.com/error"),
            patch(
                "storydiff.rss.extractor.trafilatura.fetch_url",
                side_effect=Exception("network error"),
            ),
        ):
            text, url = extractor.extract("https://example.com/error")
        assert text is None


class TestResolveUrl:
    def test_non_google_url_passthrough(self):
        from storydiff.rss.extractor import resolve_url

        assert resolve_url("https://bbc.com/article/123") == "https://bbc.com/article/123"

    def test_google_news_url_resolved(self):
        from storydiff.rss.extractor import resolve_url

        with patch("storydiff.rss.extractor.httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_resp = mock_client.head.return_value
            mock_resp.url = "https://thehindu.com/news/article123"
            result = resolve_url("https://news.google.com/rss/articles/CBMi123")
        assert result == "https://thehindu.com/news/article123"
