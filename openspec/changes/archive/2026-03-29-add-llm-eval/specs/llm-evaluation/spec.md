## ADDED Requirements

### Requirement: Eval tests are isolated from the standard test suite
The system SHALL store all LLM evaluation tests under `backend/tests/eval/`. The standard `pytest` run (i.e., `uv run pytest`) SHALL NOT execute tests in `tests/eval/`. Eval tests SHALL only run when explicitly invoked with `pytest tests/eval/`.

#### Scenario: Standard pytest run skips eval tests
- **WHEN** `uv run pytest` is executed (no path argument)
- **THEN** no tests under `tests/eval/` are collected or run

#### Scenario: Explicit eval run collects eval tests
- **WHEN** `uv run pytest tests/eval/ -v` is executed with LLM_PROVIDER configured
- **THEN** all eval test files are collected and executed against the real LLM

### Requirement: Eval suite covers category classification quality
The system SHALL include a DeepEval test in `tests/eval/test_classify.py` that evaluates the classification LLM node using a hardcoded labeled dataset of at least 10 (article_text, expected_category) pairs. The test SHALL report exact-match accuracy and SHALL use `GEval` to assess whether the predicted category is semantically appropriate for the article content.

#### Scenario: Classification accuracy measured on labeled set
- **WHEN** `test_classify.py` runs against the real LLM
- **THEN** each article in the fixture is classified and the result is compared to the expected category; the test asserts accuracy >= 0.7 and GEval score >= 0.7

### Requirement: Eval suite covers entity extraction quality
The system SHALL include a DeepEval test in `tests/eval/test_entities.py` that evaluates entity extraction using `GEval` with a criterion assessing completeness (all important named entities present) and precision (no hallucinated entities) against a labeled fixture of at least 5 (article_text, expected_entities) pairs.

#### Scenario: Entity extraction evaluated for completeness and precision
- **WHEN** `test_entities.py` runs against the real LLM
- **THEN** each article is processed and GEval scores for completeness and hallucination are computed; the test asserts mean GEval score >= 0.7

### Requirement: Eval suite covers article summary and score quality
The system SHALL include a DeepEval test in `tests/eval/test_summary_scores.py` that evaluates the `summary_scores` LangGraph node. Three metrics SHALL be applied: `SummarizationMetric` (summary faithfulness to source), `HallucinationMetric` (summary does not introduce facts absent from the article), and `GEval` (framing_polarity in [-1,1], novel_claim_score in [0,1], reliability_score in [0,1], polarity_labels is a non-empty list of strings).

#### Scenario: Summary faithfulness checked
- **WHEN** `test_summary_scores.py` runs against the real LLM with fixture article texts
- **THEN** SummarizationMetric score >= 0.5 for each article and HallucinationMetric score >= 0.5

#### Scenario: Score structure validated
- **WHEN** the summary_scores node output is evaluated
- **THEN** GEval asserts that all numeric scores are within their declared ranges and polarity_labels is a list

### Requirement: Eval suite covers consensus summary (RAG) quality
The system SHALL include a DeepEval test in `tests/eval/test_consensus.py` that evaluates the topic refresh RAG pipeline. Three metrics SHALL be applied: `FaithfulnessMetric` (consensus summary grounded in the input articles), `AnswerRelevancyMetric` (summary stays on-topic), and `GEval` for neutrality (summary does not disproportionately amplify any single article's framing). The fixture SHALL contain at least 3 manually assembled article clusters.

#### Scenario: Consensus summary faithfulness measured
- **WHEN** `test_consensus.py` runs with a multi-article cluster fixture
- **THEN** FaithfulnessMetric score >= 0.5 and AnswerRelevancyMetric score >= 0.5 for each cluster

#### Scenario: Neutrality assessed by LLM judge
- **WHEN** GEval evaluates the consensus summary against the criterion "the summary is neutral and covers perspectives from multiple sources"
- **THEN** GEval score >= 0.5

### Requirement: Eval conftest configures DeepEval judge
The `tests/eval/conftest.py` SHALL configure DeepEval to use OpenAI as the LLM judge (defaulting to `gpt-4o-mini`). It SHALL read `OPENAI_API_KEY` from the environment and raise a clear error if it is absent when eval tests are collected.

#### Scenario: Missing OPENAI_API_KEY raises informative error
- **WHEN** `pytest tests/eval/` is run without `OPENAI_API_KEY` set
- **THEN** pytest collection fails with a message instructing the developer to set `OPENAI_API_KEY`

### Requirement: DeepEval and netra-sdk dependencies are declared
`deepeval` SHALL be added to the `dev` dependency group in `backend/pyproject.toml`. `netra-sdk` SHALL be added to both the runtime `dependencies` list and the `dev` group.

#### Scenario: Fresh install includes eval tools
- **WHEN** `uv sync --group dev` is run in a clean environment
- **THEN** both `deepeval` and `netra-sdk` are available for import
