"""DeepEval tests for the article summary + scores LLM node.

Evaluates: summary faithfulness (SummarizationMetric), hallucination
(HallucinationMetric), and score structure validity (GEval).

Run:
    cd backend && uv run pytest tests/eval/test_summary_scores.py -v
"""

from __future__ import annotations

import pytest

from storydiff.analysis.json_utils import parse_json_object
from storydiff.analysis.llm import build_chat_client
from storydiff.analysis.prompts import SUMMARY_SCORES_SYSTEM

# ---------------------------------------------------------------------------
# Fixtures: article texts for summary + score evaluation
# ---------------------------------------------------------------------------
SUMMARY_FIXTURES = [
    (
        "The Federal Reserve raised interest rates by 25 basis points on Wednesday, lifting the "
        "federal funds rate to a 22-year high of 5.25-5.50%. Chair Jerome Powell signaled that "
        "further hikes were possible if inflation did not cool faster. Markets sold off sharply, "
        "with the S&P 500 dropping 1.3% and the 10-year Treasury yield rising to 4.6%. "
        "The decision was unanimous among the 12 Federal Open Market Committee members. "
        "Mortgage rates are expected to climb above 8% in response, further cooling an already "
        "depressed housing market. Consumer advocacy groups criticized the move as punishing "
        "working-class Americans already struggling with high prices."
    ),
    (
        "Scientists announced the discovery of a previously unknown species of deep-sea fish "
        "near the Mariana Trench, living at depths exceeding 8,000 meters. The species, named "
        "Pseudoliparis swirei, can withstand pressures 800 times greater than at sea level. "
        "Researchers from the Woods Hole Oceanographic Institution captured specimens using "
        "remotely operated vehicles. The find suggests the deep ocean harbors far more biodiversity "
        "than previously thought. The study was published in Nature Ecology & Evolution."
    ),
    (
        "Protests erupted in three major cities after the government announced sweeping austerity "
        "measures that would cut public sector wages by 15% and reduce pension payments for "
        "retirees. Trade unions called a general strike for next Tuesday, warning of escalating "
        "action if the measures are not withdrawn. The finance minister defended the cuts as "
        "necessary to avoid a sovereign debt default, citing a primary deficit of 8% of GDP. "
        "Opposition lawmakers introduced a no-confidence motion in parliament."
    ),
    (
        "Amazon Web Services unveiled a new family of AI inference chips called Trainium3, "
        "claiming a 40% improvement in performance per watt compared to the previous generation. "
        "The chips are designed to run large language models at lower cost than NVIDIA's H100 GPUs. "
        "AWS CEO Matt Garman said the hardware would be available to cloud customers by mid-2025. "
        "NVIDIA shares fell 2% on the news. Industry analysts noted that cloud providers are "
        "increasingly investing in proprietary silicon to reduce dependency on third-party suppliers."
    ),
    (
        "A new mRNA therapy successfully reversed Type 1 diabetes in a small clinical trial of "
        "15 patients, restoring insulin production for up to 18 months without immunosuppressants. "
        "Researchers at the University of Pennsylvania said the approach reprograms the immune "
        "system to stop attacking pancreatic beta cells. If larger trials confirm the results, the "
        "therapy could offer the first functional cure for the condition. The National Institutes "
        "of Health funded the research, which was published in the New England Journal of Medicine."
    ),
]


def _run_summary_scores(llm, article_text: str) -> dict:
    """Call the SUMMARY_SCORES_SYSTEM prompt and return parsed output."""
    raw = llm.complete_json_system_user(
        SUMMARY_SCORES_SYSTEM, f"Article:\n{article_text[:8000]}"
    )
    return parse_json_object(raw)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def llm():
    return build_chat_client()


@pytest.fixture(scope="module")
def outputs(llm):
    """Run the summary_scores node once for all fixtures."""
    return [_run_summary_scores(llm, text) for text in SUMMARY_FIXTURES]


def test_summary_faithfulness(outputs):
    """SummarizationMetric: summary is faithful to source; HallucinationMetric: no hallucinations."""
    from deepeval.metrics import HallucinationMetric, SummarizationMetric
    from deepeval.test_case import LLMTestCase

    from .conftest import get_judge_model

    judge = get_judge_model()
    sum_metric = SummarizationMetric(threshold=0.5, model=judge)
    hall_metric = HallucinationMetric(threshold=0.5, model=judge)

    sum_scores = []
    hall_scores = []

    for article, output in zip(SUMMARY_FIXTURES, outputs):
        summary = output.get("summary") or ""
        tc_sum = LLMTestCase(input=article[:600], actual_output=summary)
        tc_hall = LLMTestCase(
            input=article[:600],
            actual_output=summary,
            context=[article[:1500]],
        )
        sum_metric.measure(tc_sum)
        hall_metric.measure(tc_hall)
        sum_scores.append(sum_metric.score)
        hall_scores.append(hall_metric.score)
        print(f"  summarization={sum_metric.score:.3f} hallucination={hall_metric.score:.3f}")

    mean_sum = sum(sum_scores) / len(sum_scores)
    mean_hall = sum(hall_scores) / len(hall_scores)
    print(f"\nMean SummarizationMetric: {mean_sum:.3f}")
    print(f"Mean HallucinationMetric: {mean_hall:.3f}")

    assert mean_sum >= 0.5, f"SummarizationMetric mean {mean_sum:.3f} below 0.50"
    assert mean_hall >= 0.5, f"HallucinationMetric mean {mean_hall:.3f} below 0.50"


def test_score_structure(outputs):
    """GEval: numeric scores are in valid ranges and polarity_labels is a non-empty list."""
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    from .conftest import get_judge_model

    metric = GEval(
        name="ScoreStructureValidity",
        criteria=(
            "The output is a JSON object. Evaluate whether ALL of the following hold:\n"
            "1. framing_polarity is null or a float strictly between -1 and 1 (inclusive)\n"
            "2. novel_claim_score is null or a float between 0 and 1 (inclusive)\n"
            "3. reliability_score is null or a float between 0 and 1 (inclusive)\n"
            "4. polarity_labels is a non-empty list of short descriptive strings\n"
            "5. summary is a non-empty string\n"
            "Score 1.0 if all hold. Deduct for each violation."
        ),
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        model=get_judge_model(),
        threshold=0.7,
    )

    scores = []
    for output in outputs:
        import json
        tc = LLMTestCase(
            input="score structure check",
            actual_output=json.dumps(output),
        )
        metric.measure(tc)
        scores.append(metric.score)
        print(f"  score={metric.score:.3f} fp={output.get('framing_polarity')} labels={output.get('polarity_labels')}")

    mean_score = sum(scores) / len(scores)
    print(f"\nGEval mean score structure validity: {mean_score:.3f}")
    assert mean_score >= 0.7, f"GEval mean {mean_score:.3f} below threshold 0.70"
