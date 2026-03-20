"""LangGraph Postgres checkpointer (thread-scoped persistence / resumption)."""

from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING

from psycopg import errors as psycopg_errors
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from storydiff.db.session import get_database_url

if TYPE_CHECKING:
    from langgraph.checkpoint.postgres import PostgresSaver

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None
_saver: PostgresSaver | None = None
_setup_lock = threading.Lock()


def is_checkpoint_enabled() -> bool:
    raw = os.environ.get("LANGGRAPH_CHECKPOINT_ENABLED", "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def sqlalchemy_to_psycopg_conninfo(url: str) -> str:
    """Convert SQLAlchemy URL (``postgresql+psycopg://``) to a psycopg ``conninfo`` string."""
    if url.startswith("postgresql+psycopg://"):
        return "postgresql://" + url[len("postgresql+psycopg://") :]
    if url.startswith("postgresql://"):
        return url
    raise ValueError(
        f"Unsupported database URL for LangGraph checkpoint (expected postgresql or postgresql+psycopg): {url[:48]}…"
    )


def get_checkpoint_conninfo() -> str:
    """Connection string for the checkpointer (defaults to ``CHECKPOINT_DATABASE_URL`` or ``DATABASE_URL``)."""
    override = os.environ.get("CHECKPOINT_DATABASE_URL", "").strip()
    if override:
        return sqlalchemy_to_psycopg_conninfo(override)
    return sqlalchemy_to_psycopg_conninfo(get_database_url())


def analysis_thread_id(article_id: int) -> str:
    """Stable LangGraph ``thread_id`` for one article analysis run."""
    return f"article-analysis-{int(article_id)}"


def _insert_next_checkpoint_migration_version(pool: ConnectionPool) -> bool:
    """Insert a single ``checkpoint_migrations`` row if behind ``len(MIGRATIONS)-1``.

    Returns True if a row was inserted (or attempted). Used when ``setup()`` hits
    ``DuplicateColumn`` because DDL ran but the journal row for that step was not recorded.
    """
    from langgraph.checkpoint.postgres.base import BasePostgresSaver

    expected_last = len(BasePostgresSaver.MIGRATIONS) - 1
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(MAX(v), -1) AS max_v FROM checkpoint_migrations"
            )
            row = cur.fetchone()
            max_v = int(row["max_v"]) if row is not None else -1
            if max_v >= expected_last:
                return False
            next_v = max_v + 1
            cur.execute(
                "INSERT INTO checkpoint_migrations (v) VALUES (%s) ON CONFLICT (v) DO NOTHING",
                (next_v,),
            )
            return True


def _run_postgres_saver_setup(saver: PostgresSaver, pool: ConnectionPool) -> None:
    """Run ``PostgresSaver.setup()``; repair migration journal on duplicate DDL errors."""
    max_attempts = 12
    for attempt in range(max_attempts):
        try:
            saver.setup()
            return
        except psycopg_errors.DuplicateColumn as e:
            logger.warning(
                "LangGraph checkpoint setup DuplicateColumn (attempt %s/%s): %s — "
                "bumping migration journal if possible",
                attempt + 1,
                max_attempts,
                e,
            )
            if not _insert_next_checkpoint_migration_version(pool):
                raise
        except psycopg_errors.DuplicateTable as e:
            logger.warning(
                "LangGraph checkpoint setup DuplicateTable (attempt %s/%s): %s",
                attempt + 1,
                max_attempts,
                e,
            )
            if not _insert_next_checkpoint_migration_version(pool):
                raise


def get_postgres_saver() -> PostgresSaver:
    """Singleton ``PostgresSaver`` backed by a connection pool; calls ``setup()`` once."""
    global _pool, _saver
    if _saver is not None:
        return _saver
    with _setup_lock:
        if _saver is not None:
            return _saver
        from langgraph.checkpoint.postgres import PostgresSaver

        conninfo = get_checkpoint_conninfo()
        logger.info("LangGraph checkpoint: connecting PostgresSaver (%s)", conninfo.split("@")[-1])
        pool = ConnectionPool(
            conninfo=conninfo,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
            min_size=1,
            max_size=int(os.environ.get("LANGGRAPH_CHECKPOINT_POOL_MAX", "5")),
        )
        saver = PostgresSaver(pool)
        try:
            _run_postgres_saver_setup(saver, pool)
        except Exception:
            try:
                pool.close()
            except Exception:
                logger.exception("Error closing checkpoint pool after failed setup")
            raise
        _pool = pool
        _saver = saver
        logger.info("LangGraph checkpoint tables ready")
        return _saver


def get_postgres_saver_optional() -> PostgresSaver | None:
    if not is_checkpoint_enabled():
        return None
    return get_postgres_saver()


def close_checkpoint_resources() -> None:
    """Close the checkpoint pool (call on worker shutdown)."""
    global _pool, _saver
    with _setup_lock:
        if _pool is not None:
            try:
                _pool.close()
            except Exception:
                logger.exception("Error closing LangGraph checkpoint pool")
            _pool = None
            _saver = None
