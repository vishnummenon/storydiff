"""LangGraph checkpoint URL helpers."""

from __future__ import annotations

from storydiff.analysis.checkpointing import analysis_thread_id, sqlalchemy_to_psycopg_conninfo


def test_sqlalchemy_to_psycopg_conninfo() -> None:
    assert (
        sqlalchemy_to_psycopg_conninfo("postgresql+psycopg://u:p@localhost:5434/db")
        == "postgresql://u:p@localhost:5434/db"
    )
    assert sqlalchemy_to_psycopg_conninfo("postgresql://u:p@h/db") == "postgresql://u:p@h/db"


def test_analysis_thread_id_stable() -> None:
    assert analysis_thread_id(42) == "article-analysis-42"
