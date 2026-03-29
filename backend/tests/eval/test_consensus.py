"""DeepEval tests for the consensus summary (RAG) pipeline.

Evaluates the topic_refresh consensus generation: faithfulness to source
articles, answer relevancy, and neutrality across multiple perspectives.

The test calls the LLM directly with CONSENSUS_REFRESH_SYSTEM rather than
spinning up a full database + Qdrant setup.

Run:
    cd backend && uv run pytest tests/eval/test_consensus.py -v
"""

from __future__ import annotations

import pytest

from storydiff.analysis.json_utils import parse_json_object
from storydiff.analysis.llm import build_chat_client
from storydiff.analysis.prompts import CONSENSUS_REFRESH_SYSTEM

# ---------------------------------------------------------------------------
# Fixtures: article clusters — each cluster is a list of article texts
# representing different perspectives on the same developing story.
# ---------------------------------------------------------------------------
CONSENSUS_CLUSTERS = [
    # Cluster 1: Fed rate decision — economic, worker, and market perspectives
    {
        "topic": "Federal Reserve interest rate decision March 2025",
        "articles": [
            (
                "The Federal Reserve voted unanimously to hold interest rates at 5.25-5.50% on "
                "Wednesday, citing stubborn inflation and a resilient labor market. Chair Jerome Powell "
                "said the committee needs more confidence that inflation is on a sustainable path to 2% "
                "before cutting rates. The decision disappointed investors hoping for an early pivot."
            ),
            (
                "Consumer advocacy groups criticized the Fed's decision to keep rates high, warning "
                "that elevated borrowing costs are squeezing working families. Mortgage rates near 7.5% "
                "have effectively frozen the housing market, shutting first-time buyers out. The National "
                "Consumer Law Center called for the Fed to prioritize its full-employment mandate."
            ),
            (
                "Wall Street analysts broadly welcomed the Fed's data-dependent stance. Goldman Sachs "
                "maintained its forecast of two rate cuts in the second half of 2025. Corporate bond "
                "issuance remained robust, suggesting that businesses are adjusting to the higher-rate "
                "environment. The S&P 500 closed flat after an initial dip following the announcement."
            ),
            (
                "Economists are divided on the Fed's timing. A University of Chicago survey found that "
                "52% of prominent economists believe the Fed risks a hard landing by maintaining rates "
                "too long, while 38% think the current stance is appropriate. Historical parallels to "
                "the 1994-1995 soft landing were frequently cited in academic commentary."
            ),
        ],
    },
    # Cluster 2: AI regulation — tech industry, government, and civil society
    {
        "topic": "EU AI Act implementation 2025",
        "articles": [
            (
                "The European Union's AI Act entered its first compliance phase on February 2, requiring "
                "companies to remove or remediate AI systems deemed unacceptably risky, including real-time "
                "biometric surveillance in public spaces. Companies have 24 months to comply with rules "
                "governing high-risk AI systems in hiring, credit scoring, and critical infrastructure."
            ),
            (
                "Tech industry groups warned that the AI Act's compliance burden could cost European "
                "startups up to €300,000 per product launch, accelerating the flight of AI talent to "
                "the United States and Singapore. The CEO of a Berlin-based AI firm said she had already "
                "begun relocating her R&D team to London to escape the regulatory overhead."
            ),
            (
                "Digital rights advocates praised the AI Act as a landmark step toward accountable AI. "
                "The European Digital Rights network said the prohibition on mass surveillance and "
                "emotion recognition systems addresses real harms documented over the past decade. "
                "They called on the European AI Office to enforce rules vigorously from day one."
            ),
        ],
    },
    # Cluster 3: Climate summit — diplomatic, scientific, and developing-world angles
    {
        "topic": "COP30 climate negotiations outcome",
        "articles": [
            (
                "Nations at COP30 in Belem, Brazil, agreed to a deal that requires wealthy countries "
                "to triple climate finance to $300 billion annually by 2035. The agreement also included "
                "a renewed commitment to phase out unabated coal power by 2040 in developed economies. "
                "US climate envoy John Podesta called the deal a historic step forward."
            ),
            (
                "Scientists said the COP30 pledges fall far short of what is needed to limit warming to "
                "1.5°C. An analysis by Climate Action Tracker found that current national commitments "
                "put the world on track for 2.4°C by 2100. Researchers called for a 60% cut in global "
                "emissions by 2035, versus the 43% implied by current policies."
            ),
            (
                "Developing nations expressed mixed feelings about the COP30 outcome. The Alliance of "
                "Small Island States welcomed the finance commitment but said the $300 billion figure "
                "is still inadequate for adaptation needs. Representatives from Bangladesh and Mozambique "
                "argued that loss-and-damage funding remained underfunded relative to actual climate costs."
            ),
            (
                "Energy corporations lobbied heavily at COP30, with over 2,400 fossil fuel industry "
                "representatives attending — up 25% from COP29. Oil and gas majors pushed back against "
                "language calling for an 'unabated phase-out' of fossil fuels, securing softer wording "
                "in the final text. Environmental groups condemned the industry's outsized influence."
            ),
        ],
    },
]


def _run_consensus(llm, articles: list[str]) -> str:
    """Call the consensus refresh prompt and return the summary string."""
    combined = "\n\n---\n\n".join(f"Article {i+1}:\n{a}" for i, a in enumerate(articles))
    raw = llm.complete_json_system_user(
        CONSENSUS_REFRESH_SYSTEM, f"Articles:\n{combined[:10000]}"
    )
    data = parse_json_object(raw)
    return data.get("summary") or ""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def llm():
    return build_chat_client()


@pytest.fixture(scope="module")
def consensus_outputs(llm):
    """Generate consensus summaries for all clusters once."""
    return [
        {
            "topic": cluster["topic"],
            "articles": cluster["articles"],
            "summary": _run_consensus(llm, cluster["articles"]),
        }
        for cluster in CONSENSUS_CLUSTERS
    ]


def test_consensus_faithfulness(consensus_outputs):
    """FaithfulnessMetric: summary must be grounded in the input articles."""
    from deepeval.metrics import FaithfulnessMetric
    from deepeval.test_case import LLMTestCase

    from tests.eval.conftest import get_judge_model

    metric = FaithfulnessMetric(threshold=0.5, model=get_judge_model())
    scores = []

    for item in consensus_outputs:
        tc = LLMTestCase(
            input=item["topic"],
            actual_output=item["summary"],
            retrieval_context=item["articles"],
        )
        metric.measure(tc)
        scores.append(metric.score)
        print(f"  [{item['topic'][:40]}] faithfulness={metric.score:.3f}")

    mean = sum(scores) / len(scores)
    print(f"\nMean FaithfulnessMetric: {mean:.3f}")
    assert mean >= 0.5, f"Mean faithfulness {mean:.3f} below threshold 0.50"


def test_consensus_relevancy(consensus_outputs):
    """AnswerRelevancyMetric: summary stays on-topic relative to the cluster query."""
    from deepeval.metrics import AnswerRelevancyMetric
    from deepeval.test_case import LLMTestCase

    from tests.eval.conftest import get_judge_model

    metric = AnswerRelevancyMetric(threshold=0.5, model=get_judge_model())
    scores = []

    for item in consensus_outputs:
        tc = LLMTestCase(
            input=item["topic"],
            actual_output=item["summary"],
        )
        metric.measure(tc)
        scores.append(metric.score)
        print(f"  [{item['topic'][:40]}] relevancy={metric.score:.3f}")

    mean = sum(scores) / len(scores)
    print(f"\nMean AnswerRelevancyMetric: {mean:.3f}")
    assert mean >= 0.5, f"Mean relevancy {mean:.3f} below threshold 0.50"


def test_consensus_neutrality(consensus_outputs):
    """GEval: summary is neutral and represents multiple perspectives."""
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    from tests.eval.conftest import get_judge_model

    metric = GEval(
        name="ConsensusNeutrality",
        criteria=(
            "The consensus summary should be neutral journalistic synthesis of multiple articles "
            "about the same event. Score 1.0 if: "
            "(a) the summary does not disproportionately amplify any single article's framing or tone, "
            "(b) it acknowledges that different sources hold different perspectives where relevant, and "
            "(c) it avoids loaded language that favors one side. "
            "Deduct if the summary reads as if it were written from only one article's point of view."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=get_judge_model(),
        threshold=0.5,
    )

    scores = []
    for item in consensus_outputs:
        tc = LLMTestCase(
            input=item["topic"],
            actual_output=item["summary"],
        )
        metric.measure(tc)
        scores.append(metric.score)
        print(f"  [{item['topic'][:40]}] neutrality={metric.score:.3f}")

    mean = sum(scores) / len(scores)
    print(f"\nGEval mean neutrality: {mean:.3f}")
    assert mean >= 0.5, f"Mean neutrality {mean:.3f} below threshold 0.50"
