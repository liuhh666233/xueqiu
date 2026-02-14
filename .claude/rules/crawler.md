---
paths:
  - "scraper/crawler.py"
---

# Crawler

Orchestrates article scraping: list pages → fetch detail → extract content → save to disk.

## Key Files

| File | Role |
|------|------|
| `scraper/crawler.py` | `sync_articles`, `backfill_comments`, `AdaptiveDelay`, `_fetch_full_article` |

## Architecture / Data Flow

```
sync_articles():
  for each list page:
    fetch_article_list() → filter new articles via manifest
    for each new article:
      _fetch_full_article() → fetch_article_detail() + html_to_markdown() + fetch_all_author_comments()
      save_article() → save_manifest()

backfill_comments():
  for each manifest entry with comments_fetched=False:
    fetch_all_author_comments() → append_comments_to_article() → save_manifest()
```

## Design Patterns

- **AdaptiveDelay**: Self-adjusting delay — decreases on success (×0.9), doubles on failure, with ±50% jitter
- **Batch pauses**: Every 5 articles, takes a 30-60s random pause to avoid detection
- **Page-level manifest saves**: Manifest is saved after each list page for crash resilience
- **Non-fatal comment fetch**: Comment failures are logged but don't stop article download; marked for backfill

## Gotchas

- Detail endpoint uses `config.request_delay * 3` as base delay (stricter WAF limits)
- `_fetch_full_article` sets `comments_failed=True` when `skip_comments` is enabled (for later backfill)
- `backfill_comments` reads `manifest.user_id` for the author ID — manifest must have been populated by a prior sync

## How to Extend

1. To add a new sync strategy, follow the `sync_articles` pattern: load manifest → iterate → save per page
2. To adjust rate limiting, modify `AdaptiveDelay` parameters or `BATCH_PAUSE_*` constants

## Testing

No dedicated tests — orchestration logic depends on network calls. Core logic tested via `storage` and `models` tests.
