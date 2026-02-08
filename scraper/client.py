"""HTTP client factory for Xueqiu API requests."""

import httpx

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

    Args:
        cookie: The ``xq_a_token`` cookie value.
        timeout: Request timeout in seconds.

    Returns:
        A configured httpx.Client instance. Caller is responsible for
        closing it (use as context manager).
    """
    return httpx.Client(
        base_url=BASE_URL,
        headers=DEFAULT_HEADERS,
        cookies={"xq_a_token": cookie},
        timeout=timeout,
        follow_redirects=True,
    )
