---
paths:
  - "scraper/content.py"
  - "tests/test_content.py"
  - "tests/fixtures/article_page.html"
---

# Content

HTML content extraction and HTML-to-Markdown conversion for Xueqiu articles.

## Key Files

| File | Role |
|------|------|
| `scraper/content.py` | `extract_article_html`, `html_to_markdown`, tree walker |
| `tests/test_content.py` | Extraction and conversion tests |
| `tests/fixtures/article_page.html` | Sample article HTML page |

## Architecture / Data Flow

```
Full page HTML → extract_article_html()
                   ├─ _extract_via_xpath()        (strategy 1: DOM)
                   └─ _extract_via_script_json()   (strategy 2: embedded JS data)
                 → article body HTML

Article body HTML → html_to_markdown()
                     → lxml.etree.HTML() parse
                     → _walk_node() recursive tree walk
                     → Markdown string
```

## Design Patterns

- **Dual extraction strategy**: XPath first, then embedded JSON fallback (Xueqiu uses client-side rendering)
- **Recursive tree walker**: `_walk_node` handles block elements, `_inline_to_markdown` handles inline elements
- **Protocol-relative URL fix**: `//` prefixed image URLs are converted to `https://`

## Gotchas

- lxml is required (`from lxml import etree`) — not a stdlib dependency
- The `ARTICLE_XPATH` targets `div.article__bd__detail` — if Xueqiu changes their DOM structure, extraction breaks
- `_strip_tags` is a last-resort fallback that loses all formatting

## Testing

- **Framework**: unittest
- **Run**: `python -m unittest tests/test_content.py -v`
