"""Dedupe key generation per architecture/db_schema.md §6."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse


def normalize_title(title: str) -> str:
    s = unicodedata.normalize("NFKC", title.strip())
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_canonical_url(url: str) -> str:
    raw = url.strip()
    p = urlparse(raw)
    scheme = (p.scheme or "https").lower()
    netloc = p.netloc.lower()
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((scheme, netloc, path, p.params, p.query, ""))


def hour_bucket_utc(published_at: datetime) -> str:
    if published_at.tzinfo is None:
        dt = published_at.replace(tzinfo=timezone.utc)
    else:
        dt = published_at.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d-%H")


def compute_dedupe_key(
    *,
    canonical_url: str | None,
    source_article_id: str | None,
    media_outlet_id: int,
    title: str,
    published_at: datetime,
) -> str:
    """Return sha256 hex digest used as ``dedupe_key`` and ``article_fingerprint``."""

    cu = (canonical_url or "").strip()
    if cu:
        material = normalize_canonical_url(cu)
    else:
        sid = (source_article_id or "").strip()
        if sid:
            material = f"{sid}:{media_outlet_id}"
        else:
            nt = normalize_title(title)
            material = f"{nt}:{media_outlet_id}:{hour_bucket_utc(published_at)}"

    return hashlib.sha256(material.encode("utf-8")).hexdigest()
