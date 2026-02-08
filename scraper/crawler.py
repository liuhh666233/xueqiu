"""Orchestrate article scraping: list → fetch → extract → save."""

import random
import time

import httpx
from loguru import logger

# Take a longer break every BATCH_PAUSE_EVERY articles to look less robotic.
BATCH_PAUSE_EVERY = 5
BATCH_PAUSE_RANGE = (30.0, 60.0)


class AdaptiveDelay:
    """Self-adjusting delay with random jitter.

    On success the delay slowly decreases back toward *min_delay*;
    on failure (WAF hit, HTTP error) it doubles up to *max_delay*.
    Each call to :meth:`wait` adds ±50 % jitter so consecutive
    requests are never equally spaced.

    Args:
        base: Starting delay in seconds.
        min_delay: Lower bound in seconds.
        max_delay: Upper bound in seconds.
        jitter: Fractional jitter range (0.5 → ±50 %).
    """

    def __init__(
        self,
        base: float,
        min_delay: float = 3.0,
        max_delay: float = 120.0,
        jitter: float = 0.5,
    ) -> None:
        self.current = base
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def success(self) -> None:
        """Decrease delay after a successful request."""
        self.current = max(self.min_delay, self.current * 0.9)

    def failure(self) -> None:
        """Increase delay after a failed / rate-limited request."""
        self.current = min(self.max_delay, self.current * 2)

    def wait(self) -> None:
        """Sleep for the current delay with random jitter."""
        delay = self.current * random.uniform(
            1 - self.jitter, 1 + self.jitter
        )
        time.sleep(delay)

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
    SyncManifestEntry,
)
from scraper.storage import (
    append_comments_to_article,
    load_manifest,
    save_article,
    save_manifest,
)


def sync_articles(client: httpx.Client, config: ScraperConfig) -> int:
    """Download all new articles for the configured user, one page at a time.

    Processes each page of the article list immediately: fetches the list page,
    downloads any new articles found on it, and saves the manifest before
    moving to the next page. This spreads requests evenly and allows resuming
    from any point.

    Args:
        client: Configured httpx client.
        config: Scraper configuration.

    Returns:
        Number of newly downloaded articles.
    """
    manifest = load_manifest(config.data_dir)
    manifest.user_id = config.user_id
    downloaded = 0
    page = 1
    # Detail endpoint has stricter WAF limits than the list endpoint,
    # so use a longer base delay before each article fetch.
    delay = AdaptiveDelay(base=config.request_delay * 3)

    while True:
        logger.debug("Fetching article list page {}", page)
        resp = fetch_article_list(
            client,
            config.user_id,
            page=page,
            count=config.page_size,
        )

        new_on_page = [a for a in resp.articles if not manifest.has_article(a.id)]

        if new_on_page:
            logger.info(
                "Page {}: {} new article(s) to download", page, len(new_on_page)
            )

        for i, summary in enumerate(new_on_page, 1):
            # Batch pause: take a longer break every N articles
            if downloaded > 0 and downloaded % BATCH_PAUSE_EVERY == 0:
                pause = random.uniform(*BATCH_PAUSE_RANGE)
                logger.info(
                    "Batch pause after {} articles, sleeping {:.0f}s",
                    downloaded,
                    pause,
                )
                time.sleep(pause)

            delay.wait()
            logger.info(
                "[page {} {}/{}] Fetching: {} ({})",
                page,
                i,
                len(new_on_page),
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
                        comments_fetched=not full.comments_fetch_failed,
                    )
                )
                downloaded += 1
                delay.success()

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "HTTP error fetching article {}: {}",
                    summary.id,
                    exc,
                )
                delay.failure()
            except Exception as exc:
                logger.error(
                    "Failed to process article {}: {}",
                    summary.id,
                    exc,
                )
                delay.failure()

        # Save manifest after each page to preserve progress
        save_manifest(config.data_dir, manifest)

        if page >= resp.maxPage or not resp.articles:
            break

        if config.max_pages and page >= config.max_pages:
            logger.info("Reached max_pages limit ({})", config.max_pages)
            break

        page += 1

    logger.info("Downloaded {} new articles", downloaded)
    return downloaded


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

    # Fetch author's supplementary notes (non-fatal if it fails)
    try:
        author_comments = fetch_all_author_comments(
            client,
            summary.id,
            user_id,
            request_delay=config.request_delay,
        )
    except Exception as exc:
        logger.warning(
            "Failed to fetch comments for article {}: {}", summary.id, exc
        )
        author_comments = []
        comments_failed = True
    else:
        comments_failed = False

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
        comments_fetch_failed=comments_failed,
    )


def backfill_comments(client: httpx.Client, config: ScraperConfig) -> int:
    """Re-fetch author comments for articles where the initial fetch failed.

    Iterates through manifest entries with ``comments_fetched=False``,
    fetches the comments, appends them to the existing Markdown file,
    and updates the manifest.

    Args:
        client: Configured httpx client.
        config: Scraper configuration.

    Returns:
        Number of articles that were backfilled.
    """
    from pathlib import Path

    manifest = load_manifest(config.data_dir)
    pending = {
        aid: entry
        for aid, entry in manifest.articles.items()
        if not entry.comments_fetched
    }

    if not pending:
        logger.info("No articles need comment backfill")
        return 0

    logger.info("{} article(s) need comment backfill", len(pending))
    backfilled = 0
    delay = AdaptiveDelay(base=config.request_delay * 3)

    for article_id_str, entry in pending.items():
        # Batch pause
        if backfilled > 0 and backfilled % BATCH_PAUSE_EVERY == 0:
            pause = random.uniform(*BATCH_PAUSE_RANGE)
            logger.info(
                "Batch pause after {} articles, sleeping {:.0f}s",
                backfilled,
                pause,
            )
            time.sleep(pause)

        delay.wait()
        article_id = int(article_id_str)
        user_id = manifest.user_id

        logger.info(
            "Backfilling comments for: {} ({})", entry.title, article_id
        )

        try:
            comments = fetch_all_author_comments(
                client,
                article_id,
                user_id,
                request_delay=config.request_delay,
            )
        except Exception as exc:
            logger.error(
                "Failed to fetch comments for article {}: {}",
                article_id,
                exc,
            )
            delay.failure()
            continue

        file_path = Path(entry.file_path)
        if comments:
            append_comments_to_article(file_path, comments)

        entry.comments_fetched = True
        save_manifest(config.data_dir, manifest)
        backfilled += 1
        delay.success()

    logger.info("Backfilled comments for {} article(s)", backfilled)
    return backfilled
