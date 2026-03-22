"""Ingestion business logic: media outlet resolution, dedupe, upsert, events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from storydiff.db.models import Article, MediaOutlet
from storydiff.ingestion.dedupe import (
    compute_dedupe_key,
    normalize_canonical_url,
    normalize_title,
)
from storydiff.ingestion.exceptions import IngestionClientError
from storydiff.ingestion.publisher import EventPublisher, utc_iso_z
from storydiff.ingestion.schemas import IngestRequest


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _same_payload(existing: Article, body: IngestRequest, media_outlet_id: int) -> bool:
    if existing.media_outlet_id != media_outlet_id:
        return False
    if existing.url.strip() != body.url.strip():
        return False
    if normalize_canonical_url(existing.canonical_url) != normalize_canonical_url(body.canonical_url):
        return False
    if normalize_title(existing.title) != normalize_title(body.title):
        return False
    lang = (body.language or "en").strip() or "en"
    if existing.language.strip() != lang:
        return False
    if _to_utc(existing.published_at) != _to_utc(body.published_at):
        return False
    if (existing.raw_text or "") != (body.raw_text or ""):
        return False
    if (existing.snippet or "") != (body.snippet or ""):
        return False
    if (existing.source_category or "") != (body.source_category or ""):
        return False
    if (existing.source_article_id or "") != (body.source_article_id or ""):
        return False
    return True


@dataclass(frozen=True)
class IngestResult:
    article_id: int
    dedupe_status: str
    processing_status: str


class IngestionService:
    def ingest(
        self,
        session: Session,
        body: IngestRequest,
        publisher: EventPublisher,
    ) -> IngestResult:
        outlet = session.execute(
            select(MediaOutlet).where(
                MediaOutlet.slug == body.media_outlet_slug.strip(),
                MediaOutlet.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if outlet is None:
            raise IngestionClientError(
                "MEDIA_OUTLET_NOT_FOUND",
                f"No active media outlet with slug {body.media_outlet_slug!r}",
                status_code=404,
            )

        dedupe_key = compute_dedupe_key(
            canonical_url=body.canonical_url,
            source_article_id=body.source_article_id,
            media_outlet_id=outlet.id,
            title=body.title,
            published_at=body.published_at,
        )
        fingerprint = dedupe_key

        existing = session.execute(select(Article).where(Article.dedupe_key == dedupe_key)).scalar_one_or_none()

        if existing is None:
            article = Article(
                source_article_id=body.source_article_id,
                media_outlet_id=outlet.id,
                url=body.url.strip(),
                canonical_url=body.canonical_url.strip(),
                title=body.title.strip(),
                raw_text=body.raw_text,
                snippet=body.snippet,
                language=(body.language or "en").strip() or "en",
                published_at=_to_utc(body.published_at),
                source_category=body.source_category,
                article_fingerprint=fingerprint,
                dedupe_key=dedupe_key,
                processing_status="pending",
            )
            session.add(article)
            session.flush()
            result = IngestResult(
                article_id=article.id,
                dedupe_status="inserted",
                processing_status="pending",
            )
            session.commit()
            self._publish_after_commit(
                publisher=publisher,
                article_id=article.id,
                media_outlet_id=outlet.id,
                published_at=article.published_at,
                dedupe_status=result.dedupe_status,
            )
            return result

        if _same_payload(existing, body, outlet.id):
            session.commit()
            result = IngestResult(
                article_id=existing.id,
                dedupe_status="duplicate_ignored",
                processing_status=existing.processing_status,
            )
            # No DB write; still emit article.ingested per spec (successful persistence semantics:
            # row already exists; treat as idempotent success).
            self._publish_after_commit(
                publisher=publisher,
                article_id=existing.id,
                media_outlet_id=outlet.id,
                published_at=existing.published_at,
                dedupe_status=result.dedupe_status,
            )
            return result

        existing.source_article_id = body.source_article_id
        existing.media_outlet_id = outlet.id
        existing.url = body.url.strip()
        existing.canonical_url = body.canonical_url.strip()
        existing.title = body.title.strip()
        existing.raw_text = body.raw_text
        existing.snippet = body.snippet
        existing.language = (body.language or "en").strip() or "en"
        existing.published_at = _to_utc(body.published_at)
        existing.source_category = body.source_category
        existing.article_fingerprint = fingerprint
        existing.processing_status = "pending"
        session.flush()
        result = IngestResult(
            article_id=existing.id,
            dedupe_status="updated",
            processing_status="pending",
        )
        session.commit()
        self._publish_after_commit(
            publisher=publisher,
            article_id=existing.id,
            media_outlet_id=outlet.id,
            published_at=existing.published_at,
            dedupe_status=result.dedupe_status,
        )
        return result

    def _publish_after_commit(
        self,
        *,
        publisher: EventPublisher,
        article_id: int,
        media_outlet_id: int,
        published_at: datetime,
        dedupe_status: str,
    ) -> None:
        occurred = utc_iso_z()
        ingested_payload = {
            "event_type": "article.ingested",
            "article_id": article_id,
            "media_outlet_id": media_outlet_id,
            "published_at": utc_iso_z(published_at),
            "dedupe_status": dedupe_status,
            "occurred_at": occurred,
        }
        publisher.publish_article_ingested(ingested_payload)
        if dedupe_status in ("inserted", "updated"):
            analyze_payload = {
                "event_type": "article.analyze",
                "article_id": article_id,
                "occurred_at": occurred,
            }
            publisher.publish_article_analyze(analyze_payload)
