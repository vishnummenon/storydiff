"""LLM prompts for analysis nodes (JSON-only replies)."""

from __future__ import annotations

CLASSIFY_SYSTEM = """You classify news articles into exactly one category from the list, or null if none apply.
Reply with JSON only, no markdown: {"category_slug": "<slug from list>"} or {"category_slug": null}.
"""

ENTITIES_SYSTEM = """Extract notable named entities from the article. Reply with JSON only, no markdown:
{"entities": [{"entity_text": str, "normalized_entity": str|null, "entity_type": str|null, "salience_score": number|null}]}
Use entity_type like PERSON, ORG, GPE, EVENT when obvious; salience 0-1."""

SUMMARY_SCORES_SYSTEM = """Summarize the article and assign heuristic scores. Reply with JSON only, no markdown:
{
  "summary": string,
  "framing_polarity": number|null,
  "source_diversity_score": number|null,
  "novel_claim_score": number|null,
  "reliability_score": number|null,
  "polarity_labels": object
}
framing_polarity roughly -1 to 1; other scores 0 to 1. Omit consensus_distance (topic phase)."""
