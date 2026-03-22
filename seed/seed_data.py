#!/usr/bin/env python3
"""Seed media outlets and POST dummy articles to the ingest API.

Run from the repo (with backend deps), e.g.:
  cd backend && uv run python ../seed/seed_data.py

Requires DATABASE_URL (e.g. in backend/.env). For ingest, the API must be up;
override base URL with INGEST_BASE_URL or --base-url.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Resolve storydiff package from backend/src (this file lives in repo /seed).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_SRC = _REPO_ROOT / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

load_dotenv(_REPO_ROOT / "backend" / ".env")

from storydiff.db.models import MediaOutlet  # noqa: E402
from storydiff.db.session import get_session_local  # noqa: E402

MEDIA_OUTLETS: tuple[tuple[str, str, str], ...] = (
    ("the-hindu", "The Hindu", "thehindu.com"),
    ("the-times", "The Times of India", "timesofindia.indiatimes.com"),
    ("the-new-indian-express", "The New Indian Express", "newindianexpress.com"),
)


def ensure_media_outlets(session: Session) -> None:
    for slug, name, domain in MEDIA_OUTLETS:
        row = session.execute(select(MediaOutlet).where(MediaOutlet.slug == slug)).scalar_one_or_none()
        if row is None:
            session.add(MediaOutlet(slug=slug, name=name, domain=domain, is_active=True))
        elif not row.is_active:
            row.is_active = True
    session.commit()


def ingest_all(base_url: str, articles: list[dict]) -> None:
    import httpx

    base = base_url.rstrip("/")
    with httpx.Client(base_url=base, timeout=120.0) as client:
        try:
            client.get("/health")
        except httpx.ConnectError as exc:
            raise SystemExit(
                f"Cannot reach API at {base!r} (GET /health failed). "
                "Start the backend (e.g. uv run uvicorn storydiff.main:app) or pass --base-url."
            ) from exc
        for i, body in enumerate(articles, start=1):
            r = client.post("/api/v1/ingest", json=body)
            title = body.get("title", "")[:60]
            if r.is_success:
                data = r.json().get("data") or {}
                aid = data.get("article_id")
                status = data.get("dedupe_status")
                print(f"[{i}/{len(articles)}] ok article_id={aid} dedupe={status} — {title!r}")
            else:
                try:
                    err = r.json()
                except Exception:
                    err = r.text
                print(f"[{i}/{len(articles)}] FAILED {r.status_code} — {title!r}\n  {err}")
                r.raise_for_status()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed media outlets and ingest dummy news JSON.")
    parser.add_argument(
        "--json-path",
        type=Path,
        default=Path(__file__).resolve().parent / "news_articles.json",
        help="Path to news_articles.json (array of ingest payloads).",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("INGEST_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        help="API origin (default: INGEST_BASE_URL or http://127.0.0.1:8000).",
    )
    parser.add_argument(
        "--outlets-only",
        action="store_true",
        help="Only upsert media_outlets rows; do not call ingest.",
    )
    args = parser.parse_args()

    raw = args.json_path.read_text(encoding="utf-8")
    articles: list[dict] = json.loads(raw)
    if not isinstance(articles, list):
        raise SystemExit("Expected JSON array of ingest bodies")

    SessionLocal = get_session_local()
    with SessionLocal() as session:
        ensure_media_outlets(session)

    print(f"Ensured {len(MEDIA_OUTLETS)} media outlets in database.")

    if args.outlets_only:
        return

    ingest_all(args.base_url, articles)


if __name__ == "__main__":
    main()
