---
paths:
  - "scraper/api.py"
---

# API

Xueqiu API endpoint wrappers with WAF-aware retry logic.

## Key Files

| File | Role |
|------|------|
| `scraper/api.py` | `fetch_article_list`, `fetch_article_detail`, `fetch_comments`, `fetch_all_author_comments`, `check_auth` |

## Architecture / Data Flow

```
caller → fetch_*() → _request_with_retry() → httpx.Client.request()
                          ↓ (WAF HTML response)
                     exponential backoff + jitter → retry
```

## Design Patterns

- **Retry with backoff**: `_request_with_retry` detects WAF rate-limit (HTML instead of JSON) and retries with exponential delay + ±50% jitter
- **Retry-After header**: Honors the `Retry-After` header when present
- **Pagination**: `fetch_all_author_comments` paginates through all comment pages, filtering by author ID

## Gotchas

- WAF detection is based on `content-type` header — if response isn't JSON, it's treated as a WAF block
- `MAX_RETRIES=5` with `RETRY_BASE_DELAY=30s` means worst case ~7.5 min wait per request
- `fetch_article_detail` returns raw `dict`, not a model (HTML content in `text` field)

## How to Extend

1. Add a new `fetch_*` function that calls `_request_with_retry`
2. Define a response model in `scraper/models.py` and validate with `Model.model_validate(data)`

## Testing

No dedicated tests — API functions require network access. Tested via fixtures in model/storage tests.
