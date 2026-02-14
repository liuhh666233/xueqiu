---
paths:
  - "scraper/storage.py"
  - "tests/test_storage.py"
---

# Storage

Markdown file writing, sync manifest persistence, and filename utilities.

## Key Files

| File | Role |
|------|------|
| `scraper/storage.py` | `save_article`, `load_manifest`, `save_manifest`, `append_comments_to_article`, filename utils |
| `tests/test_storage.py` | File creation, manifest round-trip, filename sanitization tests |

## Architecture / Data Flow

```
ArticleFull → _format_article() → YAML frontmatter + Markdown
            → build_article_path() → data_dir/YYYY/YYYY-MM-DD_title_id.md
            → save_article() → write to disk

SyncManifest ↔ manifest.json (load_manifest / save_manifest)

Comments backfill → append_comments_to_article() → appends ## 补充说明 section
```

## Design Patterns

- **YAML frontmatter**: Articles are saved with `---` delimited metadata (title, date, article_id, url, counts)
- **Year-based directory structure**: `data_dir/YYYY/` subdirectories
- **Idempotent comment append**: `append_comments_to_article` skips if `## 补充说明` already exists
- **Safe filenames**: `sanitize_filename` strips non-alphanumeric/CJK chars, collapses underscores, truncates

## Gotchas

- `save_manifest` always updates `last_sync` timestamp on save
- Manifest uses string keys for article IDs (`str(article_id)`)
- `_clean_comment_text` strips HTML tags from comment text (comments may contain `<a>`, `<br/>`)

## Testing

- **Framework**: unittest
- **Run**: `python -m unittest tests/test_storage.py -v`
