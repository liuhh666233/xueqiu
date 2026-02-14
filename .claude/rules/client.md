---
paths:
  - "scraper/client.py"
---

# Client

HTTP client factory for Xueqiu API requests. Handles cookie parsing, User-Agent rotation, and browser-like headers.

## Key Files

| File | Role |
|------|------|
| `scraper/client.py` | `create_client()` factory, cookie parsing, UA rotation |

## Design Patterns

- **Event hooks**: `_rotate_user_agent` is an httpx request event hook that randomizes UA per request
- **Cookie flexibility**: `_parse_cookie_string` accepts both full browser cookie headers and bare `xq_a_token` values
- **Browser mimicry**: Default headers include `Referer`, `Origin`, `Accept-Language` to pass WAF checks

## How to Extend

1. Add new User-Agent strings to `_USER_AGENTS` list
2. Add new default headers to `DEFAULT_HEADERS` dict
3. The client is used as a context manager — always close after use

## Testing

No dedicated tests — tested indirectly through integration with `api` and `crawler` modules.
