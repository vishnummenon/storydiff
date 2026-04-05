"""RSS feed polling, article mapping, and ingest submission."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from time import mktime
from urllib.parse import urlparse

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from storydiff.db.models import MediaOutlet
from storydiff.rss.config import FeedConfig
from storydiff.rss.extractor import TextExtractor

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Convert a source name to a URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _parse_published(entry: feedparser.FeedParserDict) -> datetime:
    """Extract published datetime from a feed entry, fallback to now."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime.fromtimestamp(mktime(entry.published_parsed), tz=UTC)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime.fromtimestamp(mktime(entry.updated_parsed), tz=UTC)
    return datetime.now(UTC)


def _resolve_outlet_slug(entry: feedparser.FeedParserDict, feed: FeedConfig) -> str:
    """Resolve the outlet slug for an entry, handling Google News aggregation."""
    source = entry.get("source") if isinstance(entry, dict) else getattr(entry, "source", None)
    source_name = ""
    if isinstance(source, dict):
        source_name = source.get("title", "")
    elif source is not None:
        source_name = getattr(source, "title", "")
    if source_name and feed.source_map:
        mapped = feed.source_map.get(source_name)
        if mapped:
            return mapped
    if source_name:
        return _slugify(source_name)
    return feed.outlet_slug


def _entry_to_payload(
    entry: feedparser.FeedParserDict,
    feed: FeedConfig,
    raw_text: str | None,
    resolved_url: str | None = None,
) -> dict:
    """Map a parsed RSS entry to an IngestRequest-compatible dict."""
    rss_url = entry.get("link", "")
    url = resolved_url or rss_url
    return {
        "title": entry.get("title", ""),
        "url": url,
        "canonical_url": url,
        "published_at": _parse_published(entry).isoformat(),
        "snippet": entry.get("summary") or entry.get("description") or None,
        "raw_text": raw_text,
        "media_outlet_slug": _resolve_outlet_slug(entry, feed),
        "source_category": feed.category,
    }


def ensure_media_outlet(session: Session, slug: str, url: str) -> None:
    """Create a media_outlets row if it doesn't exist yet."""
    existing = session.execute(
        select(MediaOutlet).where(MediaOutlet.slug == slug)
    ).scalar_one_or_none()
    if existing is not None:
        return

    # Derive domain from the resolved URL, but skip aggregator domains
    parsed = urlparse(url)
    domain = parsed.netloc or ""
    aggregator_domains = {"news.google.com", "news.google.co.in", ""}
    if domain in aggregator_domains:
        # Use slug as a synthetic domain (e.g. "the-hindu" → "the-hindu.rss")
        domain = f"{slug}.rss"

    # Check if domain already taken (another outlet), make it unique
    domain_exists = session.execute(
        select(MediaOutlet).where(MediaOutlet.domain == domain)
    ).scalar_one_or_none()
    if domain_exists:
        domain = f"{slug}.rss"

    name = slug.replace("-", " ").title()
    try:
        session.add(MediaOutlet(slug=slug, name=name, domain=domain, is_active=True))
        session.commit()
        logger.info("Auto-created media outlet: %s (%s)", slug, domain)
    except IntegrityError:
        session.rollback()
        logger.debug("Media outlet %s already exists (race condition), skipping", slug)


def poll_feed(feed: FeedConfig) -> list[feedparser.FeedParserDict]:
    """Parse an RSS feed and return its entries."""
    logger.info("Polling feed: %s (%s)", feed.label or feed.url, feed.outlet_slug)
    parsed = feedparser.parse(feed.url)
    if parsed.bozo and not parsed.entries:
        logger.error("Feed parse error for %s: %s", feed.url, parsed.bozo_exception)
        return []
    logger.info("Found %d entries in %s", len(parsed.entries), feed.label or feed.url)
    return parsed.entries


def submit_articles(
    feeds: list[FeedConfig],
    extractor: TextExtractor,
    api_base_url: str,
    db_session: Session | None = None,
) -> dict[str, int]:
    """Poll all feeds, extract text, and submit to the ingest API.

    If db_session is provided, auto-creates missing media outlets.
    Returns a summary dict with counts: submitted, duplicates, errors.
    """
    stats = {"submitted": 0, "duplicates": 0, "errors": 0}
    seen_slugs: set[str] = set()

    with httpx.Client(timeout=30.0) as client:
        for feed in feeds:
            entries = poll_feed(feed)
            for entry in entries:
                url = entry.get("link", "")
                if not url:
                    continue

                title = entry.get("title", "")
                raw_text, resolved_url = extractor.extract(url)

                payload = _entry_to_payload(entry, feed, raw_text, resolved_url)
                slug = payload["media_outlet_slug"]

                # Auto-provision missing media outlets
                if db_session and slug not in seen_slugs:
                    ensure_media_outlet(db_session, slug, resolved_url)
                    seen_slugs.add(slug)

                try:
                    resp = client.post(f"{api_base_url}/api/v1/ingest", json=payload)
                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        dedupe = data.get("dedupe_status", "")
                        article_id = data.get("article_id", "?")
                        if dedupe == "duplicate_ignored":
                            logger.debug("Duplicate: %s (id=%s)", title, article_id)
                            stats["duplicates"] += 1
                        else:
                            logger.info(
                                "Submitted: %s (id=%s, status=%s)", title, article_id, dedupe
                            )
                            stats["submitted"] += 1
                    else:
                        logger.error(
                            "Ingest API error for '%s': HTTP %d — %s",
                            title,
                            resp.status_code,
                            resp.text[:200],
                        )
                        stats["errors"] += 1
                except Exception:
                    logger.error("Failed to submit '%s'", title, exc_info=True)
                    stats["errors"] += 1

    return stats
