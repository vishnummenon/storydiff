"""Tests for RSS feed configuration loading."""

from __future__ import annotations

import pytest

from storydiff.rss.config import FeedConfig, load_feeds


@pytest.fixture()
def valid_yaml(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text(
        """\
feeds:
  - url: "https://example.com/rss"
    outlet_slug: "example"
    category: "world"
    label: "Example Feed"
  - url: "https://other.com/rss"
    outlet_slug: "other"
"""
    )
    return p


@pytest.fixture()
def invalid_entry_yaml(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text(
        """\
feeds:
  - url: "https://good.com/rss"
    outlet_slug: "good"
  - url: "https://bad.com/rss"
"""
    )
    return p


@pytest.fixture()
def empty_yaml(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text("feeds: []\n")
    return p


def test_load_valid_config(valid_yaml):
    feeds = load_feeds(valid_yaml)
    assert len(feeds) == 2
    assert feeds[0].url == "https://example.com/rss"
    assert feeds[0].outlet_slug == "example"
    assert feeds[0].category == "world"
    assert feeds[0].label == "Example Feed"
    assert feeds[1].category is None


def test_invalid_entry_skipped(invalid_entry_yaml):
    feeds = load_feeds(invalid_entry_yaml)
    assert len(feeds) == 1
    assert feeds[0].outlet_slug == "good"


def test_empty_feeds_returns_empty(empty_yaml):
    feeds = load_feeds(empty_yaml)
    assert feeds == []


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_feeds("/nonexistent/feeds.yaml")


def test_missing_feeds_key(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text("other_key: true\n")
    with pytest.raises(ValueError, match="feeds"):
        load_feeds(p)


def test_source_map_loaded(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text(
        """\
feeds:
  - url: "https://news.google.com/rss"
    outlet_slug: "google-news"
    source_map:
      "Reuters": "reuters"
      "BBC News": "bbc"
"""
    )
    feeds = load_feeds(p)
    assert feeds[0].source_map == {"Reuters": "reuters", "BBC News": "bbc"}
