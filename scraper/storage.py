"""Markdown file writing, manifest persistence, and filename utilities."""

import json
import re
from datetime import datetime
from pathlib import Path

from loguru import logger

from scraper.models import ArticleFull, Comment, SyncManifest, SyncManifestEntry


def sanitize_filename(name: str, max_length: int = 50) -> str:
    """Sanitize a string for safe use in filenames.

    Removes or replaces characters that are problematic on common
    filesystems. Truncates to *max_length* characters.

    Args:
        name: Raw string (typically article title).
        max_length: Maximum character count for the result.

    Returns:
        Filesystem-safe string.
    """
    # Remove characters that are not alphanumeric, CJK, hyphen, or underscore
    safe = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', name)
    # Collapse multiple underscores
    safe = re.sub(r'_+', '_', safe).strip('_')
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip('_')
    return safe or "untitled"


def build_article_path(data_dir: Path, article: ArticleFull) -> Path:
    """Build the output file path for an article.

    Format: ``data_dir/YYYY/YYYY-MM-DD_title_id.md``

    Args:
        data_dir: Root data directory.
        article: Full article data.

    Returns:
        Path object for the Markdown file.
    """
    dt = article.created_datetime
    year_dir = data_dir / dt.strftime("%Y")
    safe_title = sanitize_filename(article.title)
    filename = f"{dt.strftime('%Y-%m-%d')}_{safe_title}_{article.id}.md"
    return year_dir / filename


def save_article(data_dir: Path, article: ArticleFull) -> Path:
    """Save an article as a Markdown file with YAML front matter.

    Args:
        data_dir: Root data directory.
        article: Full article data including content and author comments.

    Returns:
        Path to the written file.
    """
    path = build_article_path(data_dir, article)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = _format_article(article)
    path.write_text(content, encoding="utf-8")

    logger.info("Saved article: {}", path)
    return path


def _format_article(article: ArticleFull) -> str:
    """Format an article as Markdown with YAML front matter."""
    dt = article.created_datetime
    date_str = dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    # Escape quotes in title for YAML
    safe_title = article.title.replace('"', '\\"')

    lines = [
        "---",
        f'title: "{safe_title}"',
        f"date: {date_str}",
        f"article_id: {article.id}",
        f"url: {article.url}",
        f"view_count: {article.view_count}",
        f"like_count: {article.like_count}",
        "---",
        "",
        f"# {article.title}",
        "",
        article.content_markdown,
    ]

    # Append author supplementary notes if any
    if article.author_comments:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 补充说明")
        lines.append("")
        for comment in article.author_comments:
            comment_dt = comment.created_datetime
            lines.append(f"### {comment_dt.strftime('%Y-%m-%d %H:%M')}")
            lines.append("")
            lines.append(_clean_comment_text(comment.text))
            lines.append("")

    return "\n".join(lines) + "\n"


def _clean_comment_text(text: str) -> str:
    """Clean HTML tags from comment text.

    Xueqiu comment text may contain inline HTML like ``<a>`` tags
    and ``<br/>`` line breaks.
    """
    # Replace <br> variants with newline
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def load_manifest(data_dir: Path) -> SyncManifest:
    """Load the sync manifest from disk.

    Args:
        data_dir: Root data directory.

    Returns:
        SyncManifest instance. Returns an empty manifest if the file
        does not exist or is unreadable.
    """
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.exists():
        return SyncManifest()

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        return SyncManifest.model_validate(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Failed to load manifest, starting fresh: {}", exc)
        return SyncManifest()


def save_manifest(data_dir: Path, manifest: SyncManifest) -> None:
    """Persist the sync manifest to disk.

    Args:
        data_dir: Root data directory.
        manifest: Manifest to save.
    """
    manifest_path = data_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    manifest.last_sync = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    manifest_path.write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.debug("Manifest saved: {}", manifest_path)
