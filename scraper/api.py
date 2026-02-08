"""Xueqiu API endpoint wrappers."""

import json
import random
import time

import httpx
from loguru import logger

MAX_RETRIES = 5
RETRY_BASE_DELAY = 30.0
RETRY_JITTER = 0.5  # ±50% randomisation on retry delays

from scraper.models import (
    ArticleListResponse,
    ArticleSummary,
    Comment,
    CommentsResponse,
)


def fetch_article_list(
    client: httpx.Client,
    user_id: int,
    page: int = 1,
    count: int = 10,
) -> ArticleListResponse:
    """Fetch a page of original articles for a user.

    Args:
        client: Configured httpx client.
        user_id: Xueqiu user ID.
        page: Page number (1-indexed).
        count: Articles per page.

    Returns:
        Parsed article list response.
    """
    data = _request_with_retry(
        client,
        "GET",
        "/statuses/original/timeline.json",
        params={"user_id": user_id, "page": page, "count": count},
    )
    return ArticleListResponse.model_validate(data)


def fetch_article_detail(
    client: httpx.Client,
    article_id: int,
) -> dict:
    """Fetch the full article detail via JSON API.

    Uses ``/statuses/show.json`` which returns the article content
    in the ``text`` field as HTML.

    Args:
        client: Configured httpx client.
        article_id: Article/status ID.

    Returns:
        Raw JSON dict containing article fields including ``text``.
    """
    return _request_with_retry(
        client,
        "GET",
        "/statuses/show.json",
        params={"id": article_id},
    )


def fetch_comments(
    client: httpx.Client,
    article_id: int,
    page: int = 1,
    count: int = 20,
) -> CommentsResponse:
    """Fetch comments on an article.

    Args:
        client: Configured httpx client.
        article_id: Article/status ID.
        page: Page number (1-indexed).
        count: Comments per page.

    Returns:
        Parsed comments response.
    """
    data = _request_with_retry(
        client,
        "GET",
        "/statuses/comments.json",
        params={"id": article_id, "count": count, "page": page, "asc": "false"},
    )
    return CommentsResponse.model_validate(data)


def fetch_all_author_comments(
    client: httpx.Client,
    article_id: int,
    author_id: int,
    count: int = 20,
    request_delay: float = 3.0,
) -> list[Comment]:
    """Fetch all comments by the article author (补充说明).

    Paginates through all comment pages and filters for comments
    where ``comment.user.id == author_id``.

    Args:
        client: Configured httpx client.
        article_id: Article/status ID.
        author_id: User ID of the article author.
        count: Comments per page.
        request_delay: Delay between paginated requests in seconds.

    Returns:
        List of author comments sorted by creation time ascending.
    """
    author_comments: list[Comment] = []
    page = 1

    while True:
        resp = fetch_comments(client, article_id, page=page, count=count)

        for comment in resp.comments:
            if comment.user and comment.user.id == author_id:
                author_comments.append(comment)

        if page >= resp.maxPage or not resp.comments:
            break
        page += 1
        time.sleep(request_delay)

    # Sort by creation time ascending
    author_comments.sort(key=lambda c: c.created_at)
    logger.debug(
        "Article {} has {} author comments",
        article_id,
        len(author_comments),
    )
    return author_comments


def _request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    **kwargs: object,
) -> dict:
    """Make an API request with retry on WAF rate-limit responses.

    When Xueqiu's Aliyun WAF triggers due to too many requests, it
    returns HTML instead of JSON. This function retries with
    exponential backoff.

    Args:
        client: Configured httpx client.
        method: HTTP method (``GET``, ``POST``, etc.).
        url: Request URL or path.
        **kwargs: Extra arguments forwarded to ``client.request``.

    Returns:
        Parsed JSON dict.

    Raises:
        RuntimeError: If all retries are exhausted.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        resp = client.request(method, url, **kwargs)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")

        # Successful JSON response
        if "json" in content_type:
            try:
                return resp.json()
            except json.JSONDecodeError as exc:
                snippet = resp.text[:200]
                logger.error("Failed to parse JSON: {} body={}", exc, snippet)
                raise RuntimeError(
                    f"API returned non-JSON response (status {resp.status_code})."
                ) from exc

        # WAF / rate-limit: got HTML instead of JSON
        if attempt < MAX_RETRIES:
            # Honour Retry-After header when present
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    base_delay = float(retry_after)
                except ValueError:
                    base_delay = RETRY_BASE_DELAY * attempt
            else:
                base_delay = RETRY_BASE_DELAY * attempt

            # Add random jitter to avoid predictable retry patterns
            delay = base_delay * random.uniform(
                1 - RETRY_JITTER, 1 + RETRY_JITTER
            )
            logger.warning(
                "WAF rate-limit hit (attempt {}/{}), retrying in {:.0f}s...",
                attempt,
                MAX_RETRIES,
                delay,
            )
            time.sleep(delay)
        else:
            snippet = resp.text[:200]
            logger.error("API returned HTML after {} retries: {}", MAX_RETRIES, snippet)
            raise RuntimeError(
                "API returned HTML instead of JSON after retries. "
                "Cookie may be expired or WAF rate-limit is too strict. "
                "Try increasing request_delay in config."
            )


def check_auth(client: httpx.Client, user_id: int) -> bool:
    """Verify the cookie is valid by making a small API request.

    Args:
        client: Configured httpx client.
        user_id: Xueqiu user ID.

    Returns:
        True if the request succeeds, False otherwise.
    """
    try:
        resp = fetch_article_list(client, user_id, page=1, count=1)
        return resp.total > 0
    except httpx.HTTPStatusError as exc:
        logger.error("Auth check failed: {}", exc)
        return False
    except httpx.RequestError as exc:
        logger.error("Auth check request error: {}", exc)
        return False
    except RuntimeError as exc:
        logger.error("Auth check failed: {}", exc)
        return False
