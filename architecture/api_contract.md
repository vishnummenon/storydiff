## 8. API Specification

### Base Path Suggestion

```
/api/v1
```

### Common Response Envelope

Recommended shape:

```json
{
  "data": {},
  "meta": {},
  "error": null
}
```

**Common error shape:**

```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "TOPIC_NOT_FOUND",
    "message": "Topic not found"
  }
}
```

---

### 8.1 POST `/ingest`

**Purpose:**  
Accept article metadata for ingestion.

#### Request Body

```json
{
  "source_article_id": "abc-123",
  "media_outlet_slug": "reuters",
  "url": "https://example.com/news/abc-123",
  "canonical_url": "https://example.com/news/abc-123",
  "title": "Iran warns of retaliation after strike",
  "raw_text": "Optional full text if available",
  "snippet": "Optional short description",
  "language": "en",
  "published_at": "2026-03-20T08:00:00Z",
  "source_category": "world"
}
```

#### Validation Rules

- `media_outlet_slug` **required**
- `url` **required**
- `canonical_url` **required**
- `title` **required**
- `published_at` **required**
- `language` defaults to `en`

#### Success Response

```json
{
  "data": {
    "article_id": 123,
    "dedupe_status": "inserted",
    "processing_status": "pending"
  },
  "meta": {},
  "error": null
}
```

#### Possible `dedupe_status` values

- `inserted`
- `updated`
- `duplicate_ignored`

---

### 8.2 GET `/feed`

**Purpose:**  
Returns category-wise topic tiles for homepage/feed.

#### Query Parameters

- `category` (optional, slug)
- `limit_per_category` (optional, default `10`)
- `include_empty_categories` (optional, default `false`)

#### Example Response

```json
{
  "data": {
    "categories": [
      {
        "id": 2,
        "slug": "geopolitics",
        "name": "Geopolitics",
        "topics": [
          {
            "id": 44,
            "title": "Israel-Iran tensions escalate after new warnings",
            "summary": "Multiple outlets report rising tensions...",
            "article_count": 18,
            "source_count": 6,
            "reliability_score": 0.83,
            "last_updated_at": "2026-03-20T09:00:00Z"
          }
        ]
      }
    ]
  },
  "meta": {},
  "error": null
}
```

---

### 8.3 GET `/topics/{topicId}`

**Purpose:**  
Returns topic detail page payload.

#### Path Parameters

- `topicId` (required)

#### Query Parameters

- `include_articles` (optional, default: `true`)
- `include_timeline_preview` (optional, default: `true`)

#### Response

```json
{
  "data": {
    "topic": {
      "id": 44,
      "category": {
        "id": 2,
        "slug": "geopolitics",
        "name": "Geopolitics"
      },
      "canonical_label": "iran-israel-escalation-mar-2026",
      "title": "Israel-Iran tensions escalate after new warnings",
      "summary": "Across multiple outlets, the recurring narrative is...",
      "status": "active",
      "article_count": 18,
      "source_count": 6,
      "reliability_score": 0.83,
      "first_seen_at": "2026-03-20T06:00:00Z",
      "last_seen_at": "2026-03-20T09:00:00Z",
      "current_consensus_version": 3
    },
    "articles": [
      {
        "article_id": 123,
        "title": "Iran warns of retaliation after strike",
        "url": "https://example.com/news/abc-123",
        "published_at": "2026-03-20T08:00:00Z",
        "media_outlet": {
          "id": 7,
          "slug": "reuters",
          "name": "Reuters"
        },
        "summary": "The article focuses on...",
        "scores": {
          "consensus_distance": 0.21,
          "framing_polarity": 0.08,
          "source_diversity_score": 0.66,
          "novel_claim_score": 0.32,
          "reliability_score": 0.87
        },
        "polarity_labels": ["institutional_language", "low_emotive_tone"]
      }
    ],
    "timeline_preview": [
      {
        "version_no": 1,
        "generated_at": "2026-03-20T07:00:00Z",
        "title": "Initial reports of escalation"
      },
      {
        "version_no": 2,
        "generated_at": "2026-03-20T08:00:00Z",
        "title": "Tensions rise as responses harden"
      }
    ]
  },
  "meta": {},
  "error": null
}
```

---

### 8.4 GET `/topics/{topicId}/timeline`

**Purpose:**  
Returns full version history for a topic.

#### Response

```json
{
  "data": {
    "topic_id": 44,
    "versions": [
      {
        "version_no": 1,
        "title": "Initial reports of escalation",
        "summary": "Initial reporting across sources...",
        "reliability_score": 0.61,
        "article_count": 4,
        "source_count": 2,
        "generated_at": "2026-03-20T07:00:00Z"
      },
      {
        "version_no": 2,
        "title": "Tensions rise as responses harden",
        "summary": "As more outlets report...",
        "reliability_score": 0.77,
        "article_count": 10,
        "source_count": 4,
        "generated_at": "2026-03-20T08:00:00Z"
      }
    ]
  },
  "meta": {},
  "error": null
}
```

---

### 8.5 GET `/media`

**Purpose:**  
Returns publisher leaderboard / analytics list.

#### Query Parameters

- `category` (optional, slug)
- `window` (optional, default `30d`)
- `limit` (optional, default `50`)
- `sort_by` (optional):
  - `composite_rank_score`
  - `avg_consensus_distance`
  - `avg_framing_polarity`
  - `avg_novel_claim_score`

#### Response

```json
{
  "data": {
    "window": "30d",
    "category": "geopolitics",
    "items": [
      {
        "media_outlet": {
          "id": 7,
          "slug": "reuters",
          "name": "Reuters",
          "domain": "reuters.com"
        },
        "article_count": 142,
        "avg_consensus_distance": 0.19,
        "avg_framing_polarity": 0.07,
        "avg_source_diversity_score": 0.71,
        "avg_novel_claim_score": 0.22,
        "avg_reliability_score": 0.84,
        "composite_rank_score": 0.24
      }
    ]
  },
  "meta": {},
  "error": null
}
```

---

### 8.6 GET `/media/{mediaId}`

**Purpose:**  
Returns details for one publisher.

#### Response

```json
{
  "data": {
    "media_outlet": {
      "id": 7,
      "slug": "reuters",
      "name": "Reuters",
      "domain": "reuters.com"
    },
    "overall_metrics": {
      "window": "30d",
      "article_count": 320,
      "avg_consensus_distance": 0.21,
      "avg_framing_polarity": 0.09,
      "avg_source_diversity_score": 0.68,
      "avg_novel_claim_score": 0.24,
      "avg_reliability_score": 0.82,
      "composite_rank_score": 0.27
    },
    "by_category": [
      {
        "category": "geopolitics",
        "article_count": 142,
        "avg_consensus_distance": 0.19,
        "avg_framing_polarity": 0.07,
        "avg_source_diversity_score": 0.71,
        "avg_novel_claim_score": 0.22,
        "avg_reliability_score": 0.84
      }
    ],
    "recent_topics": [
      {
        "topic_id": 44,
        "title": "Israel-Iran tensions escalate after new warnings",
        "article_count": 18,
        "last_seen_at": "2026-03-20T09:00:00Z"
      }
    ]
  },
  "meta": {},
  "error": null
}
```

---

### 8.7 GET `/categories`

**Purpose:**  
Returns active categories for navigation/filtering.

#### Response

```json
{
  "data": {
    "categories": [
      {
        "id": 1,
        "slug": "politics",
        "name": "Politics",
        "display_order": 1
      },
      {
        "id": 2,
        "slug": "geopolitics",
        "name": "Geopolitics",
        "display_order": 2
      }
    ]
  },
  "meta": {},
  "error": null
}
```

---

### 8.8 GET `/search`

**Purpose:**  
Keyword / semantic / hybrid search over articles and topics.

#### Query Parameters

- `q` (**required**)
- `mode` (optional: `keyword`, `semantic`, `hybrid`)
- `type` (optional: `topics`, `articles`, `all`)
- `category` (optional, slug)
- `from` (optional, ISO datetime)
- `to` (optional, ISO datetime)
- `limit` (optional, default `20`)

#### Example Response

```json
{
  "data": {
    "query": "iran retaliation",
    "mode": "hybrid",
    "results": {
      "topics": [
        {
          "topic_id": 44,
          "title": "Israel-Iran tensions escalate after new warnings",
          "summary": "Multiple outlets report...",
          "score": 0.91
        }
      ],
      "articles": [
        {
          "article_id": 123,
          "title": "Iran warns of retaliation after strike",
          "url": "https://example.com/news/abc-123",
          "media_outlet": {
            "id": 7,
            "slug": "reuters",
            "name": "Reuters"
          },
          "published_at": "2026-03-20T08:00:00Z",
          "score": 0.87
        }
      ]
    }
  },
  "meta": {},
  "error": null
}
```

---

### 8.9 GET `/health`

**Purpose:**  
Basic service health check.

#### Response

```json
{
  "data": {
    "status": "ok"
  },
  "meta": {},
  "error": null
}
```
