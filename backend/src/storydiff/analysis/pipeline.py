"""Run the analysis LangGraph for one article."""

from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient

from storydiff.analysis.checkpointing import (
    analysis_thread_id,
    get_postgres_saver_optional,
)
from storydiff.analysis.embeddings import EmbeddingService
from storydiff.analysis.graph import AnalysisState, GraphDeps, build_analysis_graph
from storydiff.analysis.llm import build_chat_client
from storydiff.analysis.persistence import set_processing_status
from storydiff.analysis.settings import load_analysis_settings
from storydiff.db.session import get_session_local
from storydiff.ingestion.publisher import SqsPublisher
from storydiff.qdrant.settings import load_qdrant_settings

logger = logging.getLogger(__name__)


def process_article_analysis(article_id: int) -> AnalysisState:
    """Load settings, mark analyzing, run graph, return final state."""
    SessionLocal = get_session_local()
    session = SessionLocal()
    try:
        set_processing_status(session, article_id, "analyzing")
        session.commit()

        analysis_settings = load_analysis_settings()
        qcfg = load_qdrant_settings()
        embedding = EmbeddingService(qcfg.vector_size, analysis_settings)
        llm = build_chat_client(analysis_settings)
        qclient = QdrantClient(url=qcfg.url, api_key=qcfg.api_key)

        deps = GraphDeps(
            session=session,
            embedding=embedding,
            llm=llm,
            qdrant=qclient,
            qdrant_cfg=qcfg,
            analysis_settings=analysis_settings,
            events=SqsPublisher(),
        )
        checkpointer = get_postgres_saver_optional()
        graph = build_analysis_graph(deps, checkpointer=checkpointer)
        invoke_config: dict[str, Any] | None = None
        if checkpointer is not None:
            invoke_config = {
                "configurable": {"thread_id": analysis_thread_id(article_id)}
            }
        if invoke_config is not None:
            result: AnalysisState = graph.invoke({"article_id": article_id}, invoke_config)
        else:
            result = graph.invoke({"article_id": article_id})
        err = result.get("error")
        if err:
            logger.info(
                "analysis finished article_id=%s terminal_error=%s",
                article_id,
                err,
            )
        else:
            logger.info(
                "analysis finished article_id=%s ok model_version=%s",
                article_id,
                result.get("model_version", "-"),
            )
        return result
    except Exception:
        logger.exception("Analysis failed for article_id=%s", article_id)
        try:
            session.rollback()
            set_processing_status(session, article_id, "failed")
            session.commit()
        except Exception:
            logger.exception("Could not mark article %s failed", article_id)
        raise
    finally:
        session.close()


def process_article_analysis_swallow(article_id: int) -> dict[str, Any]:
    """Like ``process_article_analysis`` but returns ``{ok, error?}`` for the worker."""
    try:
        process_article_analysis(article_id)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
