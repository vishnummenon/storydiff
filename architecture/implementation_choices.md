# Open Implementation Choices

These are implementation-level decisions, not schema-level blockers.

- **Database Access:** Use SQLAlchemy.
- **Migration Tool:** Alembic.
- **Article Storage:** Store `raw_text` in full.
- **Search Ranking:** Define exact hybrid-search ranking formula.
- **Topic Embedding Strategies:**
  - summary-based only
  - title + summary
  - centroid-based
  - hybrid

**Recommended for v1:**  
Topic vector = title + summary embedding
