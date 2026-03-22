"""Pluggable chat LLM: Ollama (OpenAI-compatible) or OpenAI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from storydiff.analysis.settings import AnalysisSettings, load_analysis_settings


@runtime_checkable
class ChatClient(Protocol):
    """Minimal interface for LangGraph nodes (no vendor types in graph code)."""

    provider: str
    model: str

    def complete_json_system_user(self, system: str, user: str) -> str:
        """Return raw assistant text (JSON expected)."""
        ...


def model_version_string(client: ChatClient) -> str:
    return f"{client.provider}/{client.model}"


@dataclass
class OpenAICompatibleClient:
    """Uses the OpenAI Python SDK with configurable base URL (Ollama or OpenAI)."""

    provider: str
    model: str
    _client: Any

    def complete_json_system_user(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        choice = resp.choices[0]
        content = choice.message.content
        if not content:
            return ""
        return content


def build_chat_client(settings: AnalysisSettings | None = None) -> ChatClient:
    """Construct the active LLM client from ``LLM_PROVIDER`` and related env vars."""
    cfg = settings or load_analysis_settings()
    from openai import OpenAI

    if cfg.llm_provider == "ollama":
        base = cfg.ollama_base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = base + "/v1"
        client = OpenAI(base_url=base, api_key="ollama")
        return OpenAICompatibleClient(
            provider="ollama",
            model=cfg.ollama_model,
            _client=client,
        )

    if not cfg.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY must be set when LLM_PROVIDER=openai")
    kwargs: dict[str, Any] = {"api_key": cfg.openai_api_key}
    if cfg.openai_base_url:
        kwargs["base_url"] = cfg.openai_base_url
    client = OpenAI(**kwargs)
    return OpenAICompatibleClient(
        provider="openai",
        model=cfg.openai_model,
        _client=client,
    )
