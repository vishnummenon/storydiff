# Suggested LangGraph Outputs

## Article Analysis Graph Output

```json
{
  "article_id": 123,
  "category_id": 2,
  "entities": [],
  "topic_id": 44,
  "assignment_confidence": 0.88,
  "summary": "Article summary here",
  "scores": {
    "consensus_distance": 0.21,
    "framing_polarity": 0.08,
    "source_diversity_score": 0.66,
    "novel_claim_score": 0.32,
    "reliability_score": 0.87
  },
  "polarity_labels": ["institutional_language", "low_emotive_tone"],
  "model_version": "v1"
}
```

## Topic Refresh Graph Output

```json
{
  "topic_id": 44,
  "version_no": 3,
  "title": "Israel-Iran tensions escalate after new warnings",
  "summary": "Across multiple outlets, the recurring narrative is...",
  "reliability_score": 0.83,
  "article_count": 18,
  "source_count": 6,
  "generated_at": "2026-03-20T09:00:00Z"
}
```
