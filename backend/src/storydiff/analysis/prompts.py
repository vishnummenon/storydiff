"""LLM prompts for analysis nodes (JSON-only replies)."""

from __future__ import annotations

CLASSIFY_SYSTEM = """You assign news articles to exactly one category.

If "Existing categories" are listed in the user message:
- pick the single best-matching slug from that list (copy the slug exactly);
- set "category_slug" to that slug and set "new_category" to null.
- if none of the listed categories fit the article, set "category_slug" to null and
  propose a new category in "new_category" with a short kebab-case "slug" (lowercase,
  letters, digits, hyphens; max ~80 chars) and a human-readable "name" (title case).

If the user message says no categories exist yet (empty taxonomy):
- set "category_slug" to null and fill "new_category" with a suitable slug and name
  for this article.

Reply with JSON only, no markdown: {"category_slug": string|null, "new_category": {"slug": string, "name": string}|null}
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
