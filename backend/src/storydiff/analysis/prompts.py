"""LLM prompts for analysis nodes (JSON-only replies)."""

from __future__ import annotations

CLASSIFY_SYSTEM = """You assign news articles to exactly one category.

If "Editorial domain" is provided, prefer categories within that domain. Only assign to an existing category if it is a strong thematic match for the article. When in doubt, propose a new category rather than forcing a weak fit.

If "Existing categories" are listed in the user message:
- pick the single best-matching slug from that list (copy the slug exactly);
- set "category_slug" to that slug and set "new_category" to null.
- if none of the listed categories fit the article well, set "category_slug" to null and
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
  "polarity_labels": [string]
}
framing_polarity roughly -1 to 1; other scores 0 to 1. Omit consensus_distance (topic phase).
polarity_labels: a flat list of 2-5 short framing descriptors that characterise how this article frames the story (e.g. "pro-military action", "humanitarian concern", "diplomatic push", "economic impact"). Do NOT use generic sentiment words like "positive" or "negative"."""

CONSENSUS_REFRESH_SYSTEM = """You consolidate multiple news articles about the same developing story.
Reply with JSON only, no markdown:
{"title": string, "summary": string}
title: concise headline (max 120 characters).
summary: 2-4 neutral sentences synthesizing the evidence."""
