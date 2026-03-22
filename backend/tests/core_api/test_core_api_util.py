"""Unit tests for Core API helpers (no database)."""

from __future__ import annotations

import pytest

from storydiff.core_api.util import (
    merge_hybrid_scores,
    parse_window_to_timedelta,
    polarity_labels_to_list,
)


def test_parse_window_days():
    assert parse_window_to_timedelta("30d").days == 30


def test_parse_window_hours():
    assert parse_window_to_timedelta("24h").total_seconds() == 86400


def test_parse_window_invalid():
    with pytest.raises(ValueError):
        parse_window_to_timedelta("bad")


def test_polarity_labels():
    assert polarity_labels_to_list(None) == []
    assert polarity_labels_to_list({"a": 1, "b": 2}) == ["a", "b"]
    assert polarity_labels_to_list(["x"]) == ["x"]


def test_merge_hybrid_scores():
    s = merge_hybrid_scores(1.0, 0.5)
    assert 0.4 < s < 0.8
