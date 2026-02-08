"""HTTP client factory for Xueqiu API requests."""

import httpx
from loguru import logger

BASE_URL = "https://api.xueqiu.com"

# Browser-like headers to avoid being blocked.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://xueqiu.com/",
    "Origin": "https://xueqiu.com",
}


def _parse_cookie_string(cookie_str: str) -> dict[str, str]:
    """Parse a browser Cookie header string into a dict.

    Handles both formats:
    - Full cookie header: ``"k1=v1; k2=v2; k3=v3"``
    - Single token value: ``"abc123"`` (treated as ``xq_a_token``)

    Args:
        cookie_str: Raw cookie string from the user.

    Returns:
        Dict of cookie name-value pairs.
    """
    cookie_str = cookie_str.strip()

    # If it contains '=' it's a full cookie header string
    if "=" in cookie_str:
        cookies: dict[str, str] = {}
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if "=" in pair:
                key, _, value = pair.partition("=")
                cookies[key.strip()] = value.strip()
        return cookies

    # Otherwise treat as a bare xq_a_token value
    return {"xq_a_token": cookie_str}


def create_client(cookie: str, timeout: float = 30.0) -> httpx.Client:
    """Create an httpx client configured for Xueqiu.

    Accepts either a full browser Cookie header string (recommended,
    includes WAF cookies) or a bare ``xq_a_token`` value.

    To get the full cookie string: open browser DevTools → Network tab →
    click any request to xueqiu.com → copy the ``Cookie`` header value.

    Args:
        cookie: Full cookie header string or bare xq_a_token value.
        timeout: Request timeout in seconds.

    Returns:
        A configured httpx.Client instance. Caller is responsible for
        closing it (use as context manager).
    """
    cookies = _parse_cookie_string(cookie)
    logger.debug("Using cookies: {}", list(cookies.keys()))

    return httpx.Client(
        base_url=BASE_URL,
        headers=DEFAULT_HEADERS,
        cookies=cookies,
        timeout=timeout,
        follow_redirects=True,
    )
