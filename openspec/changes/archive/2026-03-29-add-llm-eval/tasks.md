## 1. Dependencies

- [x] 1.1 Add `netra-sdk` to runtime `dependencies` in `backend/pyproject.toml`
- [x] 1.2 Add `deepeval` to the `dev` dependency group in `backend/pyproject.toml`
- [x] 1.3 Run `uv sync --group dev` and verify both packages import without error

## 2. Observability Helper

- [x] 2.1 Create `backend/src/storydiff/observability.py` with `init_netra(service_name: str) -> None` that lazily imports `netra-sdk`, reads `NETRA_API_KEY` from env, and calls `Netra.init()` only when the key is present
- [x] 2.2 Add `# NETRA_API_KEY=` with a comment to `backend/.env.example`

## 3. Wire Netra into Entry Points

- [x] 3.1 Call `init_netra("storydiff-api")` at the top of `storydiff/main.py` (after imports, before app construction)
- [x] 3.2 Call `init_netra("storydiff-analysis-worker")` at the start of `run_worker()` in `storydiff/analysis/worker.py`
- [x] 3.3 Call `init_netra("storydiff-topic-refresh-worker")` at the start of `run_worker()` in `storydiff/topic_refresh/worker.py`

## 4. Eval Suite Scaffold

- [x] 4.1 Create `backend/tests/eval/` directory with an empty `__init__.py`
- [x] 4.2 Add `--ignore=tests/eval` to `addopts` in `[tool.pytest.ini_options]` in `backend/pyproject.toml`
- [x] 4.3 Create `backend/tests/eval/conftest.py` that reads `OPENAI_API_KEY` and raises a clear `pytest.UsageError` if it is absent; configure DeepEval to use `gpt-4o-mini` as the judge model

## 5. Category Classification Eval

- [x] 5.1 Create `backend/tests/eval/test_classify.py` with a fixture of ≥10 (article_text, expected_category) pairs covering at least 3 distinct categories
- [x] 5.2 Implement `test_classification_accuracy` that calls the `classify` LangGraph node function directly, computes exact-match accuracy, and asserts >= 0.7
- [x] 5.3 Add a `test_classification_geval` test using DeepEval `GEval` with criterion "the predicted category is appropriate for the article's main topic" and assert mean score >= 0.7

## 6. Entity Extraction Eval

- [x] 6.1 Create `backend/tests/eval/test_entities.py` with a fixture of ≥5 (article_text, expected_entities) pairs
- [x] 6.2 Implement `test_entity_completeness` using `GEval` with criterion "all important named entities (people, organizations, locations) from the article are present in the extracted list with no hallucinated entries" and assert mean score >= 0.7

## 7. Article Summary + Scores Eval

- [x] 7.1 Create `backend/tests/eval/test_summary_scores.py` with a fixture of ≥5 article texts
- [x] 7.2 Implement `test_summary_faithfulness` using DeepEval `SummarizationMetric` (input=article_text, actual_output=summary) and `HallucinationMetric`; assert both scores >= 0.5 per article
- [x] 7.3 Implement `test_score_structure` using `GEval` with criterion "framing_polarity is a float in [-1,1], novel_claim_score in [0,1], reliability_score in [0,1], polarity_labels is a non-empty list of strings" and assert score >= 0.7

## 8. Consensus Summary (RAG) Eval

- [x] 8.1 Create `backend/tests/eval/test_consensus.py` with a fixture of ≥3 manually assembled article clusters (each cluster is a list of 3–5 article texts on the same topic)
- [x] 8.2 Implement `test_consensus_faithfulness` using `FaithfulnessMetric` (retrieval_context=article_texts, actual_output=consensus_summary) and assert score >= 0.5
- [x] 8.3 Implement `test_consensus_relevancy` using `AnswerRelevancyMetric` and assert score >= 0.5
- [x] 8.4 Implement `test_consensus_neutrality` using `GEval` with criterion "the consensus summary is neutral and covers perspectives from multiple sources without disproportionately amplifying any single article's framing" and assert score >= 0.5
