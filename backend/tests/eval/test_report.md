configfile: pyproject.toml
plugins: anyio-4.12.1, deepeval-3.3.9, repeat-0.9.4, rerunfailures-12.0, xdist-3.8.0, asyncio-1.3.0, langsmith-0.7.22
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 8 items

tests/eval/test_classify.py::test_classification_accuracy
Classification accuracy: 11/11 = 1.00
PASSED

GEval mean category appropriateness score: 0.722
PASSED
[Federal Reserve interest rate decision M] faithfulness=1.000
[EU AI Act implementation 2025] faithfulness=0.800
[COP30 climate negotiations outcome] faithfulness=0.833

Mean FaithfulnessMetric: 0.878
PASSED
[Federal Reserve interest rate decision M] relevancy=1.000
[EU AI Act implementation 2025] relevancy=1.000
[COP30 climate negotiations outcome] relevancy=1.000

Mean AnswerRelevancyMetric: 1.000
PASSED
[Federal Reserve interest rate decision M] neutrality=0.799
[EU AI Act implementation 2025] neutrality=0.713
[COP30 climate negotiations outcome] neutrality=0.787

GEval mean neutrality: 0.766
PASSED
score=0.974 entities=['Biden', 'CHIPS and Science Act', 'Tuesday', 'White House', 'Intel']
score=1.000 entities=['Elon Musk', 'SpaceX', 'Starship', 'Thursday', 'Boca Chica, Texas']
score=0.980 entities=['International Monetary Fund', '2025', 'China', 'Pierre-Olivier Gourinchas', 'IMF']
score=1.000 entities=['World Health Organization', 'Marburg virus', 'Rwanda', 'Sabin Nsanzimana', 'Kigali']
score=0.967 entities=['Meta Platforms', '27%', '$39 billion', 'Q3', 'AI']

GEval mean entity completeness/precision: 0.984
PASSED
summarization=0.636 hallucination=0.000
summarization=0.000 hallucination=0.000
summarization=0.000 hallucination=0.000
summarization=0.000 hallucination=0.000
summarization=0.000 hallucination=0.000

Mean SummarizationMetric: 0.127
Mean HallucinationMetric: 0.000
FAILED
score=0.815 fp=-0.4 labels=['economic tightening', 'market reaction', 'consumer impact', 'housing market concern']
score=0.804 fp=0.5 labels=['scientific discovery', 'biodiversity expansion', 'technological achievement']
score=0.797 fp=-0.6 labels=['economic hardship', 'social unrest', 'government accountability', 'fiscal responsibility']
score=0.791 fp=0.2 labels=['technological advancement', 'market competition', 'cost efficiency', 'strategic independence']
score=0.964 fp=0.9 labels=['medical breakthrough', 'potential cure', 'scientific advancement', 'hope for patients']

GEval mean score structure validity: 0.834
PASSEDRunning teardown with pytest sessionfinish...

================================================== FAILURES ==================================================
********************\_******************** test_summary_faithfulness ********************\_\_********************

outputs = [{'framing_polarity': -0.4, 'novel_claim_score': 0.1, 'polarity_labels': ['economic tightening', 'market reaction', 'c...edical breakthrough', 'potential cure', 'scientific advancement', 'hope for patients'], 'reliability_score': 0.8, ...}]

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

>       assert mean_sum >= 0.5, f"SummarizationMetric mean {mean_sum:.3f} below 0.50"
>
> E AssertionError: SummarizationMetric mean 0.127 below 0.50
> E assert 0.12727272727272726 >= 0.5

tests/eval/test_summary_scores.py:123: AssertionError
============================================== warnings summary ==============================================
tests/eval/test_classify.py::test_classification_geval
/Users/vishnu/storydiff/backend/.venv/lib/python3.12/site-packages/deepeval/utils.py:129: DeprecationWarning: There is no current event loop
loop = asyncio.get_event_loop()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========================================== short test summary info ===========================================
FAILED tests/eval/test_summary_scores.py::test_summary_faithfulness - AssertionError: SummarizationMetric mean 0.127 below 0.50
