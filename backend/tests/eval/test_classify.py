"""DeepEval tests for the category classification LLM node.

Calls the LLM directly with the same prompt used in the analysis graph,
bypassing the database and Qdrant dependencies.

Run:
    cd backend && uv run pytest tests/eval/test_classify.py -v
"""

from __future__ import annotations

import json

import pytest

from storydiff.analysis.json_utils import parse_json_object
from storydiff.analysis.llm import build_chat_client
from storydiff.analysis.prompts import CLASSIFY_SYSTEM

# ---------------------------------------------------------------------------
# Fixtures: (article_text, expected_category_slug) pairs
# At least 10 examples covering ≥3 distinct categories.
# ---------------------------------------------------------------------------
CLASSIFY_FIXTURES = [
    # --- geopolitics ---
    (
        "The United Nations Security Council convened an emergency session on Friday to address "
        "escalating tensions between two nuclear-armed neighbors. Ambassadors traded accusations "
        "over cross-border shelling that has killed dozens of civilians in the disputed region. "
        "The US and EU called for an immediate ceasefire while China urged both sides to exercise "
        "restraint. NATO allies placed rapid-reaction forces on standby.",
        "geopolitics",
    ),
    (
        "Diplomatic negotiations between Washington and Tehran resumed in Vienna following a "
        "six-month pause. US officials confirmed that sanctions relief is back on the table if "
        "Iran agrees to roll back uranium enrichment to 3.67%. A senior Iranian negotiator said "
        "progress is possible but cautioned that domestic political pressures constrain flexibility.",
        "geopolitics",
    ),
    (
        "China's coast guard deployed water cannons against Philippine supply boats near the "
        "Second Thomas Shoal, escalating the latest standoff in the South China Sea. Manila "
        "lodged a formal protest and activated its mutual defense treaty consultations with the "
        "United States. Regional analysts warned that miscalculation could trigger a broader conflict.",
        "geopolitics",
    ),
    # --- economics / business ---
    (
        "The Federal Reserve held interest rates steady at its March meeting, signaling a cautious "
        "approach to cutting borrowing costs amid persistent inflation. Fed Chair Jerome Powell "
        "acknowledged that the labor market remains robust but warned that premature rate cuts could "
        "reignite price pressures. Markets rallied briefly before giving back gains.",
        "economics",
    ),
    (
        "OPEC+ agreed to extend production cuts of 2.2 million barrels per day through June, "
        "defying pressure from consuming nations to boost supply. Brent crude rose 2.4% on the news "
        "to $87 a barrel. Energy analysts say the cartel is managing inventories tightly ahead of "
        "the Northern Hemisphere summer driving season.",
        "economics",
    ),
    (
        "Apple reported record quarterly revenue of $124 billion, driven by strong iPhone 16 sales "
        "in emerging markets and a 15% surge in services revenue. The company announced a $110 billion "
        "share buyback and raised its dividend by 4%. Analysts said the results underscored Apple's "
        "resilience despite a broader slowdown in consumer electronics.",
        "economics",
    ),
    # --- technology ---
    (
        "OpenAI unveiled GPT-5, claiming it outperforms human experts on standardized benchmarks "
        "across medicine, law, and coding. The model introduces native multimodal reasoning and "
        "a longer 256k-token context window. Competitors Google DeepMind and Anthropic both "
        "announced accelerated release timelines for their flagship models.",
        "technology",
    ),
    (
        "The European Parliament passed the AI Act by a wide margin, creating the world's first "
        "comprehensive regulatory framework for artificial intelligence. High-risk systems such as "
        "facial recognition and hiring algorithms will require mandatory audits and human oversight. "
        "Tech lobbies warned that compliance costs could disadvantage European startups.",
        "technology",
    ),
    (
        "Researchers at MIT demonstrated a room-temperature superconductor that operates under "
        "pressures achievable with desktop equipment. If confirmed by independent labs, the "
        "breakthrough could transform energy transmission, MRI machines, and quantum computing "
        "hardware. The team published full fabrication instructions in Nature.",
        "technology",
    ),
    # --- health ---
    (
        "A phase-3 clinical trial showed that a new mRNA vaccine reduced severe RSV outcomes by "
        "83% in adults over 60. The FDA is expected to grant approval within six months, potentially "
        "preventing thousands of hospitalizations each winter. Moderna and Pfizer are both racing to "
        "bring competing candidates to market.",
        "health",
    ),
    (
        "WHO declared mpox a global health emergency for the second time in three years after a new "
        "strain spread to twelve countries outside Africa. The clade Ib variant appears more "
        "transmissible and has a higher case-fatality rate than the 2022 outbreak. Vaccine stockpiles "
        "are insufficient to meet immediate demand.",
        "health",
    ),
]

CATEGORIES = [
    {"slug": "geopolitics", "id": 1},
    {"slug": "economics", "id": 2},
    {"slug": "technology", "id": 3},
    {"slug": "health", "id": 4},
]


def _classify_article(llm, article_text: str) -> str | None:
    """Run the classify prompt and return the predicted slug (or None)."""
    lines = "\n".join(f"- slug={c['slug']!r} id={c['id']}" for c in CATEGORIES)
    user = f"Existing categories:\n{lines}\n\nArticle:\n{article_text[:8000]}"
    raw = llm.complete_json_system_user(CLASSIFY_SYSTEM, user)
    data = parse_json_object(raw)
    slug = data.get("category_slug")
    if slug:
        return str(slug).strip()
    new_cat = data.get("new_category")
    if isinstance(new_cat, dict):
        return new_cat.get("slug")
    return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def llm():
    return build_chat_client()


@pytest.fixture(scope="module")
def classifications(llm):
    """Run the classifier once for all fixtures and cache results."""
    return [_classify_article(llm, text) for text, _ in CLASSIFY_FIXTURES]


def test_classification_accuracy(classifications):
    """Exact-match accuracy must be >= 0.7 across the labeled fixture set."""
    correct = sum(
        1
        for (_, expected), predicted in zip(CLASSIFY_FIXTURES, classifications)
        if predicted == expected
    )
    total = len(CLASSIFY_FIXTURES)
    accuracy = correct / total
    print(f"\nClassification accuracy: {correct}/{total} = {accuracy:.2f}")
    assert accuracy >= 0.7, f"Classification accuracy {accuracy:.2f} below threshold 0.70"


def test_classification_geval(llm, classifications):
    """GEval: predicted category is semantically appropriate for the article."""
    from deepeval import evaluate
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    from .conftest import get_judge_model

    metric = GEval(
        name="CategoryAppropriateness",
        criteria=(
            "The predicted category slug is an appropriate label for the main topic of the article. "
            "Judge purely on semantic fit between the article content and the category name. "
            "A score of 1.0 means a perfect thematic match; 0.0 means completely wrong category."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=get_judge_model(),
        threshold=0.7,
    )

    test_cases = [
        LLMTestCase(
            input=text[:500],  # truncate for judge prompt economy
            actual_output=predicted or "unknown",
        )
        for (text, _), predicted in zip(CLASSIFY_FIXTURES, classifications)
    ]

    scores = []
    for tc in test_cases:
        metric.measure(tc)
        scores.append(metric.score)

    mean_score = sum(scores) / len(scores)
    print(f"\nGEval mean category appropriateness score: {mean_score:.3f}")
    assert mean_score >= 0.7, f"Mean GEval score {mean_score:.3f} below threshold 0.70"
