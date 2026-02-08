"""HTTP client factory for Xueqiu API requests."""

import httpx
from loguru import logger

BASE_URL = "https://xueqiu.com"

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


def create_client(cookie: str, timeout: float = 30.0) -> httpx.Client:
    """Create an httpx client configured for Xueqiu.

    Visits the homepage first to collect WAF session cookies (e.g.
    ``acw_tc``), then sets the ``xq_a_token`` auth cookie on top.

    Args:
        cookie: The ``xq_a_token`` cookie value.
        timeout: Request timeout in seconds.

    Returns:
        A configured httpx.Client instance. Caller is responsible for
        closing it (use as context manager).
    """
    client = httpx.Client(
        base_url=BASE_URL,
        headers=DEFAULT_HEADERS,
        timeout=timeout,
        follow_redirects=True,
    )

    # Visit homepage to collect WAF/session cookies
    try:
        client.get("/")
        logger.debug("Session cookies: {}", dict(client.cookies))
    except httpx.RequestError as exc:
        logger.warning("Failed to fetch homepage for session cookies: {}", exc)

    # Set the auth cookie
    client.cookies.set("xq_a_token", cookie, domain="xueqiu.com")

    return client
