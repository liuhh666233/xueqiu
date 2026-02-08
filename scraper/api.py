"""Xueqiu API endpoint wrappers."""

import httpx
from loguru import logger

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
    resp = client.get(
        "/statuses/original/timeline.json",
        params={"user_id": user_id, "page": page, "count": count},
    )
    resp.raise_for_status()
    return ArticleListResponse.model_validate(resp.json())


def fetch_article_page(
    client: httpx.Client,
    user_id: int,
    article_id: int,
) -> str:
    """Fetch the HTML page for a single article.

    Args:
        client: Configured httpx client.
        user_id: Xueqiu user ID.
        article_id: Article/status ID.

    Returns:
        Raw HTML string of the article page.
    """
    url = f"/{user_id}/{article_id}"
    resp = client.get(url)
    resp.raise_for_status()
    return resp.text


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
    resp = client.get(
        "/statuses/comments.json",
        params={"id": article_id, "count": count, "page": page, "asc": "false"},
    )
    resp.raise_for_status()
    return CommentsResponse.model_validate(resp.json())


def fetch_all_author_comments(
    client: httpx.Client,
    article_id: int,
    author_id: int,
    count: int = 20,
) -> list[Comment]:
    """Fetch all comments by the article author (补充说明).

    Paginates through all comment pages and filters for comments
    where ``comment.user.id == author_id``.

    Args:
        client: Configured httpx client.
        article_id: Article/status ID.
        author_id: User ID of the article author.
        count: Comments per page.

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

    # Sort by creation time ascending
    author_comments.sort(key=lambda c: c.created_at)
    logger.debug(
        "Article {} has {} author comments",
        article_id,
        len(author_comments),
    )
    return author_comments


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
