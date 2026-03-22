"""Shared helpers for Core Read API (windows, labels, scoring)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any


def parse_window_to_timedelta(window: str) -> timedelta:
    """Parse values like ``30d``, ``7d``, ``24h`` into a timedelta."""
    raw = window.strip().lower()
    m = re.fullmatch(r"(\d+)(d|h)", raw)
    if not m:
        raise ValueError(f"Unsupported window format: {window!r} (use e.g. 30d, 24h)")
    n = int(m.group(1))
    unit = m.group(2)
    if unit == "d":
        return timedelta(days=n)
    return timedelta(hours=n)


def window_bounds_now(window: str) -> tuple[datetime, datetime]:
    """Rolling window ending at UTC now: ``(window_start, window_end)``."""
    delta = parse_window_to_timedelta(window)
    end = datetime.now(timezone.utc)
    start = end - delta
    return start, end


def polarity_labels_to_list(raw: Any) -> list[str]:
    """Normalize ``polarity_labels_json`` to a flat list of label strings for API output.

    Handles two storage shapes:
    - list  (new): ["pro-military action", "humanitarian concern"]  → returned as-is
    - dict (legacy): {"negative": ["civilian casualties"], "positive": ["precision strikes"]}
      → values are flattened; keys (sentiment buckets) are discarded
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, dict):
        labels: list[str] = []
        for v in raw.values():
            if isinstance(v, list):
                labels.extend(str(x) for x in v)
            elif v is not None:
                labels.append(str(v))
        return labels
    return []


def composite_rank_score(
    avg_consensus_distance: float | None,
    avg_reliability: float | None,
) -> float | None:
    """Blend distance + reliability into a single leaderboard score (higher is better)."""
    if avg_reliability is None and avg_consensus_distance is None:
        return None
    rel = float(avg_reliability) if avg_reliability is not None else 0.5
    dist = float(avg_consensus_distance) if avg_consensus_distance is not None else 0.5
    # Higher reliability and lower consensus distance (disagreement) => higher composite
    return max(0.0, min(1.0, 0.5 * rel + 0.5 * (1.0 - dist)))


def merge_hybrid_scores(
    keyword_score: float | None,
    semantic_score: float | None,
    *,
    keyword_weight: float = 0.45,
    semantic_weight: float = 0.55,
) -> float:
    """Combine keyword presence (0–1) and semantic similarity (0–1).

    Keyword matches are treated as 1.0 when present; semantic scores are already 0–1 from Qdrant.
    """
    k = keyword_score if keyword_score is not None else 0.0
    s = semantic_score if semantic_score is not None else 0.0
    return keyword_weight * k + semantic_weight * s
