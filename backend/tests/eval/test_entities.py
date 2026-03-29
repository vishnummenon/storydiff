"""DeepEval tests for the entity extraction LLM node.

Calls the LLM directly with the same ENTITIES_SYSTEM prompt used in the
analysis graph, then evaluates completeness and precision via GEval.

Run:
    cd backend && uv run pytest tests/eval/test_entities.py -v
"""

from __future__ import annotations

import pytest

from storydiff.analysis.json_utils import parse_json_object
from storydiff.analysis.llm import build_chat_client
from storydiff.analysis.prompts import ENTITIES_SYSTEM

# ---------------------------------------------------------------------------
# Fixtures: (article_text, expected_key_entities)
# expected_key_entities lists the important entities a good extractor should find.
# ---------------------------------------------------------------------------
ENTITY_FIXTURES = [
    (
        "President Biden signed the CHIPS and Science Act into law on Tuesday at the White House, "
        "flanked by Intel CEO Pat Gelsinger and Commerce Secretary Gina Raimondo. The legislation "
        "allocates $52 billion to semiconductor manufacturing incentives and $200 billion for "
        "scientific research. Critics from the Republican Party argued the bill was inflationary.",
        ["Joe Biden", "Intel", "Pat Gelsinger", "Gina Raimondo", "CHIPS and Science Act", "Republican Party"],
    ),
    (
        "Elon Musk's SpaceX launched the Starship vehicle for the fourth time on Thursday from "
        "Boca Chica, Texas. The Super Heavy booster successfully returned to the launch site, "
        "while the Starship upper stage completed a controlled splashdown in the Indian Ocean. "
        "NASA Administrator Bill Nelson praised the milestone as critical to the Artemis lunar program.",
        ["Elon Musk", "SpaceX", "Starship", "Boca Chica", "Texas", "NASA", "Bill Nelson", "Artemis"],
    ),
    (
        "The International Monetary Fund revised its global growth forecast down to 2.9% for 2025, "
        "citing sticky inflation in advanced economies and a real estate slump in China. IMF chief "
        "economist Pierre-Olivier Gourinchas warned that central banks must remain vigilant. "
        "Germany and Japan were singled out as the weakest performers among G7 nations.",
        ["International Monetary Fund", "IMF", "Pierre-Olivier Gourinchas", "China", "Germany", "Japan", "G7"],
    ),
    (
        "The World Health Organization declared the Marburg virus outbreak in Rwanda a public health "
        "emergency of international concern after 15 deaths were confirmed. Rwanda's health minister "
        "Sabin Nsanzimana said contact-tracing teams had identified 200 potential exposures. "
        "The outbreak is centered in Kigali, the capital.",
        ["World Health Organization", "WHO", "Rwanda", "Marburg", "Sabin Nsanzimana", "Kigali"],
    ),
    (
        "Meta Platforms reported a 27% surge in advertising revenue to $39 billion in Q3, driven by "
        "AI-powered ad targeting across Facebook and Instagram. CEO Mark Zuckerberg announced a new "
        "augmented-reality headset called Orion, which he described as the most advanced AR device "
        "ever built. Shares rose 4% in after-hours trading on the Nasdaq.",
        ["Meta Platforms", "Facebook", "Instagram", "Mark Zuckerberg", "Orion", "Nasdaq"],
    ),
]


def _extract_entities(llm, article_text: str) -> list[str]:
    """Run entity extraction and return a list of entity_text values."""
    raw = llm.complete_json_system_user(
        ENTITIES_SYSTEM, f"Article:\n{article_text[:8000]}"
    )
    data = parse_json_object(raw)
    ents = data.get("entities") or []
    return [e.get("entity_text", "") for e in ents if isinstance(e, dict)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def llm():
    return build_chat_client()


@pytest.fixture(scope="module")
def extractions(llm):
    """Run entity extraction once for all fixtures and cache."""
    return [_extract_entities(llm, text) for text, _ in ENTITY_FIXTURES]


def test_entity_completeness(llm, extractions):
    """GEval: all important entities are present, no hallucinations."""
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    from tests.eval.conftest import get_judge_model

    metric = GEval(
        name="EntityCompletenessAndPrecision",
        criteria=(
            "Evaluate the extracted entity list against the article. "
            "Score 1.0 if: (a) all important named entities — people, organizations, locations, "
            "events, and products mentioned prominently — are present, AND (b) the list contains "
            "no hallucinated entities that do not appear in the article. "
            "Deduct proportionally for missing important entities or hallucinated entries. "
            "Minor formatting differences (e.g., 'Joe Biden' vs 'Biden') are acceptable."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=get_judge_model(),
        threshold=0.7,
    )

    scores = []
    for (text, _), extracted in zip(ENTITY_FIXTURES, extractions):
        tc = LLMTestCase(
            input=text[:600],
            actual_output=", ".join(extracted) if extracted else "(none)",
        )
        metric.measure(tc)
        scores.append(metric.score)
        print(f"  score={metric.score:.3f} entities={extracted[:5]}")

    mean_score = sum(scores) / len(scores)
    print(f"\nGEval mean entity completeness/precision: {mean_score:.3f}")
    assert mean_score >= 0.7, f"Mean GEval score {mean_score:.3f} below threshold 0.70"
