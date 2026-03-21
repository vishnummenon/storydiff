"""Fixtures for Core Read API tests (requires PostgreSQL)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from storydiff.db import Base
from storydiff.db import models  # noqa: F401 — register all tables
from storydiff.db.models import Category, MediaOutlet, Topic
from storydiff.db.session import get_db
from storydiff.main import app


def _test_database_url() -> str:
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@127.0.0.1:5434/storydiff",
    )


def _topics_table_matches_orm(engine) -> bool:
    """ORM expects migrated schema (e.g. ``last_consensus_refresh_at`` on ``topics``)."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'topics' "
                "AND column_name = 'last_consensus_refresh_at'"
            )
        ).fetchone()
    return row is not None


@pytest.fixture(scope="session")
def engine():
    url = _test_database_url()
    try:
        e = create_engine(url, pool_pre_ping=True)
        with e.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable for Core API tests ({url}): {exc}")
    Base.metadata.create_all(e)
    if not _topics_table_matches_orm(e):
        pytest.skip(
            "Core API tests need a migrated database (topics.last_consensus_refresh_at missing). "
            "Run: uv run alembic upgrade head against TEST_DATABASE_URL"
        )
    yield e


@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def cleanup_core_tables(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE topic_versions, topic_article_links, topics, articles, "
                "article_analysis, media_outlets, categories RESTART IDENTITY CASCADE"
            )
        )
    yield


@pytest.fixture
def sample_feed_data(db_session, cleanup_core_tables):
    now = datetime.now(timezone.utc)
    cat = Category(slug="geopolitics", name="Geopolitics", display_order=1, is_active=True)
    db_session.add(cat)
    db_session.flush()
    topic = Topic(
        category_id=cat.id,
        canonical_label="iran-test",
        current_title="Iran tensions",
        current_summary="Summary text",
        status="active",
        first_seen_at=now,
        last_seen_at=now,
        article_count=2,
        source_count=1,
        current_reliability_score=None,
        current_consensus_version=1,
    )
    db_session.add(topic)
    db_session.commit()
    db_session.refresh(cat)
    db_session.refresh(topic)
    return {"category": cat, "topic": topic}


@pytest.fixture
def client(engine, db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()
