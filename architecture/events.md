## 7. Event Payloads

### 7.1 `article.ingested`

**Meaning:**  
Article metadata successfully persisted.

**Example payload:**

```json
{
  "event_type": "article.ingested",
  "article_id": 123,
  "media_outlet_id": 7,
  "published_at": "2026-03-20T08:00:00Z",
  "dedupe_status": "inserted",
  "occurred_at": "2026-03-20T08:01:00Z"
}
```

---

### 7.2 `article.analyze`

**Meaning:**  
Trigger AI analysis workflow.

**Example payload:**

```json
{
  "event_type": "article.analyze",
  "article_id": 123,
  "occurred_at": "2026-03-20T08:01:05Z"
}
```

---

### 7.3 `topic.refresh`

**Meaning:**  
Trigger topic consensus recomputation.

**Example payload:**

```json
{
  "event_type": "topic.refresh",
  "topic_id": 44,
  "trigger_article_id": 123,
  "refresh_reason": "new_high_confidence_assignment",
  "occurred_at": "2026-03-20T08:02:30Z"
}
```
