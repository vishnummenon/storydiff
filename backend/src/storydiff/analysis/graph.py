"""LangGraph for article analysis (bounded sequential workflow)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from storydiff.analysis.embeddings import EmbeddingService
from storydiff.analysis.json_utils import parse_json_object
from storydiff.analysis.llm import ChatClient, model_version_string
from storydiff.analysis.persistence import (
    get_article_for_analysis,
    get_or_create_category,
    replace_article_entities,
    set_processing_status,
    update_article_category,
    upsert_article_analysis,
)
from storydiff.analysis.topic_assignment import TopicRefreshPublisher, assign_article_to_topic
from storydiff.analysis.prompts import CLASSIFY_SYSTEM, ENTITIES_SYSTEM, SUMMARY_SCORES_SYSTEM
from storydiff.analysis.qdrant_write import upsert_article_embedding
from storydiff.analysis.settings import AnalysisSettings
from storydiff.db.models import Category
from storydiff.qdrant.settings import QdrantSettings

logger = logging.getLogger(__name__)


def _log_step(step: str, state: AnalysisState, detail: str = "") -> None:
    """Structured INFO log for each LangGraph node (visibility in worker logs)."""
    aid = state.get("article_id")
    err = state.get("error")
    suffix = f" {detail}" if detail else ""
    if err:
        logger.info("analysis step=%s article_id=%s prior_error=%s%s", step, aid, err, suffix)
    else:
        logger.info("analysis step=%s article_id=%s%s", step, aid, suffix)


class AnalysisState(TypedDict, total=False):
    article_id: int
    error: str
    text: str
    embedding: list[float]
    category_id: int | None
    entities: list[dict[str, Any]]
    summary: str | None
    framing_polarity: float | None
    source_diversity_score: float | None
    novel_claim_score: float | None
    reliability_score: float | None
    polarity_labels_json: dict[str, Any] | None
    model_version: str
    topic_id: int | None
    consensus_distance: float | None


@dataclass
class GraphDeps:
    session: Session
    embedding: EmbeddingService
    llm: ChatClient
    qdrant: QdrantClient
    qdrant_cfg: QdrantSettings
    analysis_settings: AnalysisSettings
    events: TopicRefreshPublisher


def build_analysis_graph(
    deps: GraphDeps,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
) -> Any:
    s = deps.session
    emb = deps.embedding
    llm = deps.llm
    qclient = deps.qdrant
    qcfg = deps.qdrant_cfg
    cfg = deps.analysis_settings
    events = deps.events
    mv = model_version_string(llm)

    def n_load(state: AnalysisState) -> dict[str, Any]:
        _log_step("load", state)
        if state.get("error"):
            _log_step("load", state, "skip (prior error)")
            return {}
        aid = state["article_id"]
        article = get_article_for_analysis(s, aid)
        if not article:
            logger.info("analysis step=load article_id=%s result=article_not_found", aid)
            return {"error": "article_not_found"}
        text = (article.raw_text or article.snippet or article.title or "")[: cfg.max_text_chars]
        if not text.strip():
            logger.info("analysis step=load article_id=%s result=no_text", aid)
            return {"error": "no_text"}
        logger.info(
            "analysis step=load article_id=%s result=ok text_chars=%s",
            aid,
            len(text),
        )
        return {"text": text}

    def n_embed(state: AnalysisState) -> dict[str, Any]:
        _log_step("embed", state)
        if state.get("error"):
            _log_step("embed", state, "skip (prior error)")
            return {}
        if "text" not in state:
            logger.info("analysis step=embed article_id=%s result=no_text_key", state.get("article_id"))
            return {"error": "no_text"}
        try:
            vec = emb.embed_text(state["text"])
        except Exception as e:
            logger.exception("Embedding failed")
            return {"error": f"embedding:{e}"}
        logger.info(
            "analysis step=embed article_id=%s result=ok dim=%s",
            state["article_id"],
            len(vec),
        )
        return {"embedding": vec}

    def n_qdrant1(state: AnalysisState) -> dict[str, Any]:
        _log_step("qdrant1", state)
        if state.get("error") or "embedding" not in state:
            if state.get("error"):
                _log_step("qdrant1", state, "skip (prior error)")
            else:
                logger.info(
                    "analysis step=qdrant1 article_id=%s skip (no embedding)",
                    state.get("article_id"),
                )
            return {}
        article = get_article_for_analysis(s, state["article_id"])
        if article is None:
            logger.info(
                "analysis step=qdrant1 article_id=%s result=article_not_found",
                state.get("article_id"),
            )
            return {"error": "article_not_found"}
        try:
            upsert_article_embedding(
                qclient, qcfg.article_collection, article, state["embedding"], qcfg.vector_size
            )
        except Exception as e:
            logger.exception("Qdrant upsert failed")
            return {"error": f"qdrant:{e}"}
        logger.info(
            "analysis step=qdrant1 article_id=%s result=ok collection=%s",
            state["article_id"],
            qcfg.article_collection,
        )
        return {}

    def n_classify(state: AnalysisState) -> dict[str, Any]:
        _log_step("classify", state)
        if state.get("error"):
            _log_step("classify", state, "skip (prior error)")
            return {}
        cats = s.scalars(select(Category).where(Category.is_active == True)).all()  # noqa: E712
        body = state["text"][:8000]
        if cats:
            lines = "\n".join(f"- slug={c.slug!r} id={c.id}" for c in cats)
            user = f"Existing categories:\n{lines}\n\nArticle:\n{body}"
        else:
            user = (
                "No categories exist in the database yet. Propose exactly one new "
                "category for this article (slug + name in JSON).\n\n"
                f"Article:\n{body}"
            )
        try:
            raw = llm.complete_json_system_user(CLASSIFY_SYSTEM, user)
            data = parse_json_object(raw)
            slug = data.get("category_slug")
            new_cat = data.get("new_category")
            nc_slug: str | None = None
            nc_name: str | None = None
            if isinstance(new_cat, dict):
                nc_slug = new_cat.get("slug")
                nc_name = new_cat.get("name")
                if nc_slug is not None:
                    nc_slug = str(nc_slug)
                if nc_name is not None:
                    nc_name = str(nc_name)

            if slug is not None:
                slug = str(slug).strip()
            if slug:
                for c in cats:
                    if c.slug == slug:
                        update_article_category(s, state["article_id"], c.id)
                        s.flush()
                        logger.info(
                            "analysis step=classify article_id=%s result=ok category_id=%s slug=%s",
                            state["article_id"],
                            c.id,
                            c.slug,
                        )
                        return {"category_id": c.id}
                # slug from model but not in list — treat as new category proposal
                if nc_slug is None and nc_name is None:
                    nc_slug, nc_name = slug, slug.replace("-", " ").title()

            if nc_slug and nc_name:
                c = get_or_create_category(s, nc_slug, nc_name)
                update_article_category(s, state["article_id"], c.id)
                s.flush()
                logger.info(
                    "analysis step=classify article_id=%s result=ok category_id=%s slug=%s",
                    state["article_id"],
                    c.id,
                    c.slug,
                )
                return {"category_id": c.id}

            logger.info(
                "analysis step=classify article_id=%s result=missing_category_fields",
                state["article_id"],
            )
        except Exception as e:
            logger.warning("Classification failed: %s", e)
        return {"category_id": None}

    def n_entities(state: AnalysisState) -> dict[str, Any]:
        _log_step("entities", state)
        if state.get("error"):
            _log_step("entities", state, "skip (prior error)")
            return {}
        try:
            raw = llm.complete_json_system_user(
                ENTITIES_SYSTEM, f"Article:\n{state['text'][:8000]}"
            )
            data = parse_json_object(raw)
            ents = data.get("entities") or []
            if not isinstance(ents, list):
                ents = []
            cleaned = []
            for e in ents:
                if not isinstance(e, dict) or "entity_text" not in e:
                    continue
                cleaned.append(
                    {
                        "entity_text": str(e["entity_text"]),
                        "normalized_entity": e.get("normalized_entity"),
                        "entity_type": e.get("entity_type"),
                        "salience_score": e.get("salience_score"),
                    }
                )
            logger.info(
                "analysis step=entities article_id=%s result=ok count=%s",
                state["article_id"],
                len(cleaned),
            )
            return {"entities": cleaned}
        except Exception as e:
            logger.warning("Entity extraction failed: %s", e)
            logger.info(
                "analysis step=entities article_id=%s result=error entities_count=0",
                state.get("article_id"),
            )
            return {"entities": []}

    def n_summary_scores(state: AnalysisState) -> dict[str, Any]:
        _log_step("summary_scores", state)
        if state.get("error"):
            _log_step("summary_scores", state, "skip (prior error)")
            return {}
        try:
            raw = llm.complete_json_system_user(
                SUMMARY_SCORES_SYSTEM, f"Article:\n{state['text'][:8000]}"
            )
            data = parse_json_object(raw)
            pol = data.get("polarity_labels")
            if pol is not None and not isinstance(pol, dict):
                pol = None
            out = {
                "summary": data.get("summary"),
                "framing_polarity": _f(data.get("framing_polarity")),
                "source_diversity_score": _f(data.get("source_diversity_score")),
                "novel_claim_score": _f(data.get("novel_claim_score")),
                "reliability_score": _f(data.get("reliability_score")),
                "polarity_labels_json": pol,
            }
            sm = out.get("summary")
            logger.info(
                "analysis step=summary_scores article_id=%s result=ok summary_len=%s",
                state["article_id"],
                len(sm) if isinstance(sm, str) else 0,
            )
            return out
        except Exception as e:
            logger.warning("Summary/scores failed: %s", e)
            return {
                "summary": None,
                "framing_polarity": None,
                "source_diversity_score": None,
                "novel_claim_score": None,
                "reliability_score": None,
                "polarity_labels_json": None,
            }

    def n_topic_assign(state: AnalysisState) -> dict[str, Any]:
        _log_step("topic_assign", state)
        if state.get("error"):
            _log_step("topic_assign", state, "skip (prior error)")
            return {}
        if "embedding" not in state:
            logger.info(
                "analysis step=topic_assign article_id=%s skip (no embedding)",
                state.get("article_id"),
            )
            return {}
        aid = state["article_id"]
        article = get_article_for_analysis(s, aid)
        if article is None:
            return {"error": "article_not_found"}
        try:
            out = assign_article_to_topic(
                s,
                article,
                state["embedding"],
                state.get("entities") or [],
                state.get("summary"),
                qclient=qclient,
                qcfg=qcfg,
                cfg=cfg,
                embedder=emb,
                events=events,
            )
            logger.info(
                "analysis step=topic_assign article_id=%s result=ok topic_id=%s",
                aid,
                out.get("topic_id"),
            )
            return out
        except Exception as e:
            logger.exception("Topic assignment failed")
            return {"error": f"topic_assign:{e}"}

    def n_persist(state: AnalysisState) -> dict[str, Any]:
        _log_step("persist", state)
        if state.get("error"):
            _log_step("persist", state, "skip (prior error)")
            return {}
        aid = state["article_id"]
        now = datetime.now(timezone.utc)
        try:
            upsert_article_analysis(
                s,
                article_id=aid,
                summary=state.get("summary"),
                consensus_distance=state.get("consensus_distance"),
                framing_polarity=state.get("framing_polarity"),
                source_diversity_score=state.get("source_diversity_score"),
                novel_claim_score=state.get("novel_claim_score"),
                reliability_score=state.get("reliability_score"),
                polarity_labels_json=state.get("polarity_labels_json"),
                model_version=mv,
                analyzed_at=now,
            )
            replace_article_entities(s, aid, state.get("entities") or [])
            set_processing_status(s, aid, "analyzed")
            s.commit()
            logger.info(
                "analysis step=persist article_id=%s result=ok model_version=%s",
                aid,
                mv,
            )
        except Exception as e:
            logger.exception("Persist failed")
            s.rollback()
            return {"error": f"persist:{e}"}
        return {"model_version": mv}

    def n_qdrant2(state: AnalysisState) -> dict[str, Any]:
        _log_step("qdrant2", state)
        if state.get("error") or "embedding" not in state:
            if state.get("error"):
                _log_step("qdrant2", state, "skip (prior error)")
            else:
                logger.info(
                    "analysis step=qdrant2 article_id=%s skip (no embedding)",
                    state.get("article_id"),
                )
            return {}
        article = get_article_for_analysis(s, state["article_id"])
        if article is None:
            return {}
        try:
            upsert_article_embedding(
                qclient,
                qcfg.article_collection,
                article,
                state["embedding"],
                qcfg.vector_size,
            )
        except Exception as e:
            logger.exception("Final Qdrant upsert failed")
            return {"error": f"qdrant2:{e}"}
        logger.info(
            "analysis step=qdrant2 article_id=%s result=ok collection=%s",
            state["article_id"],
            qcfg.article_collection,
        )
        return {}

    def n_finalize(state: AnalysisState) -> dict[str, Any]:
        _log_step("finalize", state)
        if state.get("error"):
            try:
                s.rollback()
            except Exception:
                pass
            aid = state.get("article_id")
            if aid is not None:
                set_processing_status(s, int(aid), "failed")
                s.commit()
                logger.info(
                    "analysis step=finalize article_id=%s result=marked_failed error=%s",
                    aid,
                    state.get("error"),
                )
            else:
                logger.info("analysis step=finalize result=skipped (no article_id)")
        else:
            logger.info(
                "analysis step=finalize article_id=%s result=ok (no graph error)",
                state.get("article_id"),
            )
        return {}

    builder = StateGraph(AnalysisState)
    builder.add_node("load", n_load)
    builder.add_node("embed", n_embed)
    builder.add_node("qdrant1", n_qdrant1)
    builder.add_node("classify", n_classify)
    builder.add_node("entities", n_entities)
    builder.add_node("summary_scores", n_summary_scores)
    builder.add_node("topic_assign", n_topic_assign)
    builder.add_node("persist", n_persist)
    builder.add_node("qdrant2", n_qdrant2)
    builder.add_node("finalize", n_finalize)
    builder.add_edge(START, "load")
    builder.add_edge("load", "embed")
    builder.add_edge("embed", "qdrant1")
    builder.add_edge("qdrant1", "classify")
    builder.add_edge("classify", "entities")
    builder.add_edge("entities", "summary_scores")
    builder.add_edge("summary_scores", "topic_assign")
    builder.add_edge("topic_assign", "qdrant2")
    builder.add_edge("qdrant2", "persist")
    builder.add_edge("persist", "finalize")
    builder.add_edge("finalize", END)
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


def _f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
