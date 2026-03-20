"""Ollama embedding HTTP path (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from storydiff.analysis.embeddings import EmbeddingService
from storydiff.analysis.settings import AnalysisSettings


def test_embed_text_ollama_returns_384() -> None:
    settings = AnalysisSettings(
        llm_provider="ollama",
        ollama_base_url="http://127.0.0.1:11434/v1",
        ollama_model="llama3.1:8b",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
        embedding_backend="ollama",
        ollama_embed_base_url="http://127.0.0.1:11434",
        ollama_embedding_model="all-minilm",
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        max_text_chars=12000,
    )
    vec = [0.0] * 384
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={"embedding": vec})
    mock_client = MagicMock()
    mock_client.post = MagicMock(return_value=mock_resp)
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_client)
    mock_cm.__exit__ = MagicMock(return_value=False)

    with patch("storydiff.analysis.embeddings.httpx.Client", return_value=mock_cm):
        svc = EmbeddingService(expected_dim=384, settings=settings)
        out = svc.embed_text("hello")
        assert len(out) == 384
