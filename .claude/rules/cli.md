---
paths:
  - "scraper/cli.py"
  - "scraper/__main__.py"
---

# CLI

Click-based command-line interface. Entry point for all user-facing operations.

## Key Files

| File | Role |
|------|------|
| `scraper/cli.py` | Click group with `sync`, `check-auth`, `backfill-comments`, `status` commands |
| `scraper/__main__.py` | `python -m scraper` entry point |

## Commands

| Command | Description |
|---------|-------------|
| `sync` | Incremental article download. Options: `--cookie`, `--config`, `--max-pages`, `--skip-comments` |
| `check-auth` | Verify cookie validity |
| `backfill-comments` | Re-fetch comments for articles where initial fetch failed |
| `status` | Show sync statistics |

## Design Patterns

- **Config priority**: CLI args > env vars (`XUEQIU_COOKIE`) > YAML config file
- **Lazy imports**: `from pathlib import Path` is imported inside command functions to keep module load fast

## How to Extend

1. Add a new `@main.command()` function in `cli.py`
2. Load config with `load_config()`, create client with `create_client()`, call business logic from `crawler`

## Testing

No dedicated tests — CLI commands are thin wrappers around `crawler` and `api` functions.
