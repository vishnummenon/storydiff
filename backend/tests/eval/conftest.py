"""Shared configuration for DeepEval offline evaluation tests.

Run with:
    cd backend && uv run pytest tests/eval/ -v

Requires OPENAI_API_KEY to be set — DeepEval uses OpenAI as the LLM judge.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Load backend/.env so OPENAI_API_KEY (and other vars) are available without
# needing to export them manually in the shell.
_env_file = Path(__file__).parents[3] / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file, override=False)


def pytest_configure(config: pytest.Config) -> None:
    """Validate prerequisites when the eval suite is collected."""
    # Only enforce when tests/eval is actually being collected
    test_paths = [str(a) for a in config.args]
    if not any("eval" in p for p in test_paths):
        return

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise pytest.UsageError(
            "OPENAI_API_KEY is required to run eval tests (DeepEval uses OpenAI as the LLM judge).\n"
            "Set it in your environment or backend/.env before running:\n"
            "    export OPENAI_API_KEY=sk-...\n"
            "    uv run pytest tests/eval/ -v"
        )


def get_judge_model():
    """Return a configured DeepEval GPTModel for use as LLM judge."""
    from deepeval.models import GPTModel

    return GPTModel(model="gpt-4o-mini")
