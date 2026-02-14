---
paths:
  - "scraper/models.py"
  - "tests/test_models.py"
  - "tests/fixtures/article_list.json"
  - "tests/fixtures/comments.json"
---

# Models

Pydantic v2 data models for Xueqiu API responses and sync state tracking.

## Key Files

| File | Role |
|------|------|
| `scraper/models.py` | All model definitions |
| `tests/test_models.py` | Model parsing and manifest tests |
| `tests/fixtures/*.json` | Sample API response fixtures |

## Architecture / Data Flow

```
API JSON → ArticleListResponse / CommentsResponse (parsing)
         → ArticleSummary / Comment (individual items)
         → ArticleFull (assembled by crawler)
         → SyncManifest / SyncManifestEntry (persistence tracking)
```

## Design Patterns

- **Alias mapping**: `ArticleListResponse.articles` uses `alias="list"` to map from the API's `list` key
- **Computed properties**: `created_datetime` and `url` are `@property` on multiple models
- **Millisecond timestamps**: All `created_at` fields are Unix ms; properties convert to `datetime`

## How to Extend

1. Add new fields to the relevant model class with defaults (backward-compatible with existing manifests)
2. If adding a new API response type, create a new `BaseModel` subclass
3. Update fixtures in `tests/fixtures/` and add test cases in `tests/test_models.py`

## Testing

- **Framework**: unittest
- **Run**: `python -m unittest tests/test_models.py -v`
