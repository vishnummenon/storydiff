"""Persistence helpers (mock session)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from storydiff.analysis.persistence import upsert_article_analysis
from storydiff.db.models import ArticleAnalysis


def test_upsert_article_analysis_inserts_when_missing() -> None:
    session = MagicMock()
    session.get = MagicMock(return_value=None)
    now = datetime.now(timezone.utc)
    upsert_article_analysis(
        session,
        article_id=42,
        summary="s",
        consensus_distance=None,
        framing_polarity=0.1,
        source_diversity_score=None,
        novel_claim_score=None,
        reliability_score=None,
        polarity_labels_json=None,
        model_version="ollama/llama3.1:8b",
        analyzed_at=now,
    )
    session.add.assert_called_once()
    added = session.add.call_args[0][0]
    assert isinstance(added, ArticleAnalysis)
    assert added.article_id == 42


def test_upsert_article_analysis_updates_existing() -> None:
    session = MagicMock()
    row = MagicMock(spec=ArticleAnalysis)
    session.get = MagicMock(return_value=row)
    now = datetime.now(timezone.utc)
    upsert_article_analysis(
        session,
        article_id=1,
        summary="new",
        consensus_distance=None,
        framing_polarity=None,
        source_diversity_score=None,
        novel_claim_score=None,
        reliability_score=None,
        polarity_labels_json=None,
        model_version="openai/gpt-4o-mini",
        analyzed_at=now,
    )
    session.add.assert_not_called()
    assert row.summary == "new"
    assert row.model_version == "openai/gpt-4o-mini"
