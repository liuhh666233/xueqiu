"""Orchestrate article scraping: list → fetch → extract → save."""

import time

import httpx
from loguru import logger

from scraper.api import (
    fetch_all_author_comments,
    fetch_article_detail,
    fetch_article_list,
)
from scraper.config import ScraperConfig
from scraper.content import html_to_markdown
from scraper.models import (
    ArticleFull,
    ArticleSummary,
    SyncManifest,
    SyncManifestEntry,
)
from scraper.storage import (
    load_manifest,
    save_article,
    save_manifest,
)


def sync_articles(client: httpx.Client, config: ScraperConfig) -> int:
    """Download all new articles for the configured user.

    Loads the sync manifest, paginates through the article list,
    skips already-downloaded articles, and saves new ones.

    Args:
        client: Configured httpx client.
        config: Scraper configuration.

    Returns:
        Number of newly downloaded articles.
    """
    manifest = load_manifest(config.data_dir)
    manifest.user_id = config.user_id

    articles = _collect_new_articles(client, config, manifest)
    if not articles:
        logger.info("No new articles to download")
        save_manifest(config.data_dir, manifest)
        return 0

    logger.info("Found {} new articles to download", len(articles))
    downloaded = 0

    try:
        for i, summary in enumerate(articles, 1):
            logger.info(
                "[{}/{}] Fetching: {} ({})",
                i,
                len(articles),
                summary.title,
                summary.id,
            )

            try:
                full = _fetch_full_article(client, config, summary)
                path = save_article(config.data_dir, full)

                manifest.add_article(
                    SyncManifestEntry(
                        article_id=full.id,
                        title=full.title,
                        file_path=str(path),
                        synced_at=full.created_datetime.strftime(
                            "%Y-%m-%dT%H:%M:%S+08:00"
                        ),
                    )
                )
                downloaded += 1

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "HTTP error fetching article {}: {}",
                    summary.id,
                    exc,
                )
            except Exception as exc:
                logger.error(
                    "Failed to process article {}: {}",
                    summary.id,
                    exc,
                )

            # Rate limiting between articles
            if i < len(articles):
                time.sleep(config.request_delay)
    finally:
        # Always save manifest to preserve progress
        save_manifest(config.data_dir, manifest)

    logger.info("Downloaded {} new articles", downloaded)
    return downloaded


def _collect_new_articles(
    client: httpx.Client,
    config: ScraperConfig,
    manifest: SyncManifest,
) -> list[ArticleSummary]:
    """Paginate through the article list and collect IDs not yet in the manifest.

    Args:
        client: Configured httpx client.
        config: Scraper configuration.
        manifest: Current sync manifest.

    Returns:
        List of article summaries to download.
    """
    new_articles: list[ArticleSummary] = []
    page = 1

    while True:
        logger.debug("Fetching article list page {}", page)
        resp = fetch_article_list(
            client,
            config.user_id,
            page=page,
            count=config.page_size,
        )

        for article in resp.articles:
            if not manifest.has_article(article.id):
                new_articles.append(article)

        if page >= resp.maxPage or not resp.articles:
            break

        if config.max_pages and page >= config.max_pages:
            logger.info("Reached max_pages limit ({})", config.max_pages)
            break

        page += 1
        time.sleep(config.request_delay)

    return new_articles


def _fetch_full_article(
    client: httpx.Client,
    config: ScraperConfig,
    summary: ArticleSummary,
) -> ArticleFull:
    """Fetch the full content and author comments for an article.

    Args:
        client: Configured httpx client.
        config: Scraper configuration.
        summary: Article summary from the list API.

    Returns:
        ArticleFull with extracted content and author comments.
    """
    user_id = summary.user_id or (summary.user.id if summary.user else config.user_id)

    # Fetch article detail via JSON API
    detail = fetch_article_detail(client, summary.id)
    time.sleep(config.request_delay)

    # The API returns article HTML in the "text" field
    content_html = detail.get("text", "")
    content_md = html_to_markdown(content_html)

    # Fetch author's supplementary notes
    author_comments = fetch_all_author_comments(
        client,
        summary.id,
        user_id,
        request_delay=config.request_delay,
    )

    return ArticleFull(
        id=summary.id,
        title=detail.get("title", summary.title),
        content_html=content_html,
        content_markdown=content_md,
        created_at=summary.created_at,
        user_id=user_id,
        view_count=detail.get("view_count", summary.view_count),
        like_count=detail.get("fav_count", summary.like_count),
        reply_count=detail.get("reply_count", summary.reply_count),
        retweet_count=detail.get("retweet_count", summary.retweet_count),
        author_comments=author_comments,
    )
