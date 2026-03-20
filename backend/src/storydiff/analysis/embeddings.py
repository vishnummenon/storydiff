"""Dense article embeddings: Ollama ``/api/embeddings`` (default) or optional Sentence Transformers."""

from __future__ import annotations

from typing import Any

import httpx

from storydiff.analysis.settings import AnalysisSettings, load_analysis_settings


class EmbeddingService:
    """384-dim vectors for ``all-minilm`` (Ollama) or ``all-MiniLM-L6-v2`` (HF)."""

    def __init__(self, expected_dim: int, settings: AnalysisSettings | None = None) -> None:
        self._expected_dim = expected_dim
        self._settings = settings or load_analysis_settings()
        self._st_model: Any = None

    def _ensure_st(self) -> Any:
        if self._st_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise RuntimeError(
                    "EMBEDDING_BACKEND=sentence_transformers requires the optional "
                    "'embeddings-st' extra: uv sync --extra embeddings-st"
                ) from e
            self._st_model = SentenceTransformer(self._settings.embedding_model_name)
        return self._st_model

    def embed_text(self, text: str) -> list[float]:
        if self._settings.embedding_backend == "sentence_transformers":
            model = self._ensure_st()
            vec = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
            out = vec.tolist() if hasattr(vec, "tolist") else list(vec)
        else:
            out = self._ollama_embed(text)
        if len(out) != self._expected_dim:
            raise ValueError(
                f"Embedding length {len(out)} != EMBEDDING_VECTOR_SIZE {self._expected_dim}"
            )
        return [float(x) for x in out]

    def _ollama_embed(self, text: str) -> list[float]:
        base = self._settings.ollama_embed_base_url.rstrip("/")
        url = f"{base}/api/embeddings"
        payload = {
            "model": self._settings.ollama_embedding_model,
            "prompt": text,
        }
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        emb = data.get("embedding")
        if not isinstance(emb, list):
            raise ValueError("Ollama embeddings response missing 'embedding' list")
        return [float(x) for x in emb]
