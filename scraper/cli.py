"""CLI interface for the Xueqiu article scraper."""

import click
from loguru import logger

from scraper.api import check_auth
from scraper.client import create_client
from scraper.config import load_config
from scraper.crawler import backfill_comments, sync_articles
from scraper.storage import load_manifest


@click.group()
def main() -> None:
    """Xueqiu article scraper - download and sync original articles."""


@main.command()
@click.option(
    "--cookie",
    envvar="XUEQIU_COOKIE",
    help="Full browser Cookie header string (or set XUEQIU_COOKIE env var).",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=False),
    default=None,
    help="Path to YAML config file.",
)
@click.option(
    "--max-pages",
    type=int,
    default=0,
    help="Maximum number of list pages to fetch (0 = all).",
)
@click.option(
    "--skip-comments",
    is_flag=True,
    default=False,
    help="Skip fetching author comments (can backfill later).",
)
def sync(
    cookie: str | None,
    config_path: str | None,
    max_pages: int,
    skip_comments: bool,
) -> None:
    """Download all new articles (incremental sync)."""
    from pathlib import Path

    cfg = load_config(
        config_path=Path(config_path) if config_path else None,
        cookie=cookie,
    )

    if not cfg.cookie:
        raise click.UsageError(
            "Cookie is required. Use --cookie, XUEQIU_COOKIE env var, "
            "or set it in config.yaml."
        )

    if max_pages:
        cfg.max_pages = max_pages

    if skip_comments:
        cfg.skip_comments = True

    with create_client(cfg.cookie) as client:
        count = sync_articles(client, cfg)

    if count:
        click.echo(f"Downloaded {count} new article(s).")
    else:
        click.echo("Already up to date.")


@main.command("check-auth")
@click.option(
    "--cookie",
    envvar="XUEQIU_COOKIE",
    help="Full browser Cookie header string.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=False),
    default=None,
    help="Path to YAML config file.",
)
def check_auth_cmd(cookie: str | None, config_path: str | None) -> None:
    """Check if the cookie is still valid."""
    from pathlib import Path

    cfg = load_config(
        config_path=Path(config_path) if config_path else None,
        cookie=cookie,
    )

    if not cfg.cookie:
        raise click.UsageError("Cookie is required.")

    with create_client(cfg.cookie) as client:
        ok = check_auth(client, cfg.user_id)

    if ok:
        click.echo("Authentication is valid.")
    else:
        click.echo("Authentication failed. Cookie may be expired.")
        raise SystemExit(1)


@main.command("backfill-comments")
@click.option(
    "--cookie",
    envvar="XUEQIU_COOKIE",
    help="Full browser Cookie header string (or set XUEQIU_COOKIE env var).",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=False),
    default=None,
    help="Path to YAML config file.",
)
def backfill_comments_cmd(cookie: str | None, config_path: str | None) -> None:
    """Re-fetch author comments for articles where the initial fetch failed."""
    from pathlib import Path

    cfg = load_config(
        config_path=Path(config_path) if config_path else None,
        cookie=cookie,
    )

    if not cfg.cookie:
        raise click.UsageError(
            "Cookie is required. Use --cookie, XUEQIU_COOKIE env var, "
            "or set it in config.yaml."
        )

    manifest = load_manifest(cfg.data_dir)
    pending = sum(1 for e in manifest.articles.values() if not e.comments_fetched)

    if not pending:
        click.echo("All articles have comments fetched. Nothing to backfill.")
        return

    click.echo(f"{pending} article(s) need comment backfill.")

    with create_client(cfg.cookie) as client:
        count = backfill_comments(client, cfg)

    click.echo(f"Backfilled comments for {count} article(s).")


@main.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=False),
    default=None,
    help="Path to YAML config file.",
)
def status(config_path: str | None) -> None:
    """Show sync status and statistics."""
    from pathlib import Path

    cfg = load_config(config_path=Path(config_path) if config_path else None)
    manifest = load_manifest(cfg.data_dir)

    total = len(manifest.articles)
    click.echo(f"User ID: {cfg.user_id}")
    click.echo(f"Data directory: {cfg.data_dir}")
    click.echo(f"Articles downloaded: {total}")

    if manifest.last_sync:
        click.echo(f"Last sync: {manifest.last_sync}")
    else:
        click.echo("Last sync: never")
