"""Analysis worker and LLM settings from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class AnalysisSettings:
    """LLM and embedding configuration (see openspec phase-2 design)."""

    llm_provider: str  # ollama | openai
    ollama_base_url: str
    ollama_model: str
    openai_api_key: str | None
    openai_model: str
    openai_base_url: str | None
    # embedding_backend: ollama = Ollama /api/embeddings (default all-minilm, 384-d); sentence_transformers = HF
    embedding_backend: str  # ollama | sentence_transformers
    ollama_embed_base_url: str
    ollama_embedding_model: str
    embedding_model_name: str
    max_text_chars: int
    # Topic assignment (Phase 3)
    topic_candidate_top_n: int
    topic_assign_threshold: float
    topic_weight_vector: float
    topic_weight_entities: float
    topic_weight_category: float
    topic_weight_time: float
    topic_weight_recency: float
    topic_weight_source_diversity: float
    topic_entity_sample_size: int
    # Topic refresh worker
    topic_refresh_window_hours: int
    topic_refresh_cooldown_seconds: int
    topic_refresh_min_evidence: int


def load_analysis_settings() -> AnalysisSettings:
    load_dotenv(_BACKEND_ROOT / ".env")
    provider = os.environ.get("LLM_PROVIDER", "ollama").strip().lower()
    if provider not in ("ollama", "openai"):
        raise RuntimeError("LLM_PROVIDER must be 'ollama' or 'openai'")

    ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1").strip()
    ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.1:8b").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip() or None
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
    openai_base = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    emb = os.environ.get(
        "EMBEDDING_MODEL_NAME",
        "sentence-transformers/all-MiniLM-L6-v2",
    ).strip()
    max_chars = int(os.environ.get("ANALYSIS_MAX_TEXT_CHARS", "12000").strip())
    emb_backend = os.environ.get("EMBEDDING_BACKEND", "ollama").strip().lower()
    if emb_backend not in ("ollama", "sentence_transformers"):
        raise RuntimeError("EMBEDDING_BACKEND must be 'ollama' or 'sentence_transformers'")

    ollama_embed = os.environ.get("OLLAMA_EMBEDDING_BASE_URL", "").strip()
    if not ollama_embed:
        base = ollama_base.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        ollama_embed = base
    ollama_emb_model = os.environ.get("OLLAMA_EMBEDDING_MODEL", "all-minilm").strip()

    def _f(name: str, default: str) -> float:
        return float(os.environ.get(name, default).strip())

    def _i(name: str, default: str) -> int:
        return int(os.environ.get(name, default).strip())

    return AnalysisSettings(
        llm_provider=provider,
        ollama_base_url=ollama_base,
        ollama_model=ollama_model,
        openai_api_key=openai_key,
        openai_model=openai_model,
        openai_base_url=openai_base,
        embedding_backend=emb_backend,
        ollama_embed_base_url=ollama_embed,
        ollama_embedding_model=ollama_emb_model,
        embedding_model_name=emb,
        max_text_chars=max_chars,
        topic_candidate_top_n=_i("TOPIC_CANDIDATE_TOP_N", "20"),
        topic_assign_threshold=_f("TOPIC_ASSIGN_THRESHOLD", "0.45"),
        topic_weight_vector=_f("TOPIC_WEIGHT_VECTOR", "0.35"),
        topic_weight_entities=_f("TOPIC_WEIGHT_ENTITIES", "0.2"),
        topic_weight_category=_f("TOPIC_WEIGHT_CATEGORY", "0.15"),
        topic_weight_time=_f("TOPIC_WEIGHT_TIME", "0.1"),
        topic_weight_recency=_f("TOPIC_WEIGHT_RECENCY", "0.1"),
        topic_weight_source_diversity=_f("TOPIC_WEIGHT_SOURCE_DIVERSITY", "0.1"),
        topic_entity_sample_size=_i("TOPIC_ENTITY_SAMPLE_SIZE", "40"),
        topic_refresh_window_hours=_i("TOPIC_REFRESH_WINDOW_HOURS", "720"),
        topic_refresh_cooldown_seconds=_i("TOPIC_REFRESH_COOLDOWN_SECONDS", "120"),
        topic_refresh_min_evidence=_i("TOPIC_REFRESH_MIN_EVIDENCE", "1"),
    )
