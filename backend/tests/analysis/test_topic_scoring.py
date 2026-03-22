"""Unit tests for topic assignment scoring and distance helpers."""

from __future__ import annotations

from dataclasses import replace

from storydiff.analysis.settings import AnalysisSettings
from storydiff.analysis.topic_scoring import TopicSignals, entity_overlap_score, weighted_sum_score


def _base_settings() -> AnalysisSettings:
    return AnalysisSettings(
        llm_provider="ollama",
        ollama_base_url="http://127.0.0.1:11434/v1",
        ollama_model="m",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
        embedding_backend="ollama",
        ollama_embed_base_url="http://127.0.0.1:11434",
        ollama_embedding_model="all-minilm",
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        max_text_chars=12000,
        topic_candidate_top_n=20,
        topic_assign_threshold=0.45,
        topic_weight_vector=0.35,
        topic_weight_entities=0.2,
        topic_weight_category=0.15,
        topic_weight_time=0.1,
        topic_weight_recency=0.1,
        topic_weight_source_diversity=0.1,
        topic_entity_sample_size=40,
        topic_refresh_window_hours=720,
        topic_refresh_cooldown_seconds=120,
        topic_refresh_min_evidence=1,
    )


def test_weighted_sum_matches_all_ones() -> None:
    cfg = _base_settings()
    s = TopicSignals(
        vector_similarity=1.0,
        entity_overlap=1.0,
        category_match=1.0,
        time_proximity=1.0,
        topic_recency=1.0,
        source_diversity=1.0,
    )
    assert abs(weighted_sum_score(s, cfg) - 1.0) < 1e-6


def test_assignment_threshold_accepts_strong_match() -> None:
    cfg = replace(_base_settings(), topic_assign_threshold=0.5)
    s = TopicSignals(
        vector_similarity=1.0,
        entity_overlap=1.0,
        category_match=1.0,
        time_proximity=1.0,
        topic_recency=1.0,
        source_diversity=1.0,
    )
    assert weighted_sum_score(s, cfg) >= cfg.topic_assign_threshold


def test_assignment_threshold_rejects_weak_match() -> None:
    cfg = replace(_base_settings(), topic_assign_threshold=0.95)
    s = TopicSignals(
        vector_similarity=0.2,
        entity_overlap=0.0,
        category_match=0.0,
        time_proximity=0.2,
        topic_recency=0.2,
        source_diversity=0.2,
    )
    assert weighted_sum_score(s, cfg) < cfg.topic_assign_threshold


def test_entity_overlap_jaccard() -> None:
    a = {"a", "b"}
    b = {"b", "c"}
    assert abs(entity_overlap_score(a, b) - 1.0 / 3.0) < 1e-6
