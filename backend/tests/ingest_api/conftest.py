"""Fixtures for POST /api/v1/ingest tests (requires PostgreSQL)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from storydiff.db.base import Base
from storydiff.db.models import Article, MediaOutlet
from storydiff.db.session import get_db
from storydiff.main import app


def _test_database_url() -> str:
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@127.0.0.1:5434/storydiff",
    )


@pytest.fixture(scope="session")
def engine():
    url = _test_database_url()
    try:
        e = create_engine(url, pool_pre_ping=True)
        with e.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable for API tests ({url}): {exc}")
    Base.metadata.create_all(e, tables=[MediaOutlet.__table__, Article.__table__])
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
def cleanup_tables(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE articles, media_outlets RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def media_outlet(db_session, cleanup_tables):
    m = MediaOutlet(slug="reuters", name="Reuters", domain="reuters.com", is_active=True)
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


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
