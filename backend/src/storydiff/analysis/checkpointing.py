"""LangGraph Postgres checkpointer (thread-scoped persistence / resumption)."""

from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING

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
        _pool = ConnectionPool(
            conninfo=conninfo,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
            min_size=1,
            max_size=int(os.environ.get("LANGGRAPH_CHECKPOINT_POOL_MAX", "5")),
        )
        _saver = PostgresSaver(_pool)
        _saver.setup()
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
