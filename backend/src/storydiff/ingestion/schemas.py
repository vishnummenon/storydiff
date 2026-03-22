"""Pydantic models for ingestion API (architecture/api_contract.md §8.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class IngestRequest(BaseModel):
    source_article_id: str | None = None
    media_outlet_slug: str
    url: str
    canonical_url: str
    title: str
    raw_text: str | None = None
    snippet: str | None = None
    language: str | None = Field(default="en")
    published_at: datetime
    source_category: str | None = None
    model_config = {"extra": "forbid"}

    @field_validator("language", mode="before")
    @classmethod
    def default_language(cls, v: Any) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            return "en"
        return v if isinstance(v, str) else str(v)


class IngestSuccessData(BaseModel):
    article_id: int
    dedupe_status: Literal["inserted", "updated", "duplicate_ignored"]
    processing_status: str


class EnvelopeMeta(BaseModel):
    """Optional metadata; extend as needed."""

    model_config = {"extra": "allow"}


class SuccessEnvelope(BaseModel):
    data: IngestSuccessData
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    data: None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ErrorBody
