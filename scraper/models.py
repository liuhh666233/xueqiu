"""Pydantic v2 models for Xueqiu API responses and sync manifest."""

from __future__ import annotations

import builtins
from datetime import datetime

from pydantic import BaseModel, Field


class ArticleUser(BaseModel):
    """User info embedded in article responses."""

    id: int
    screen_name: str = ""


class ArticleSummary(BaseModel):
    """Summary of an article from the timeline listing API.

    Fields map to the JSON keys returned by
    ``/statuses/original/timeline.json``.
    """

    id: int
    title: str = ""
    description: str = ""
    created_at: int = Field(
        description="Unix timestamp in milliseconds",
    )
    user_id: int = 0
    user: ArticleUser | None = None
    view_count: int = 0
    like_count: int = 0
    reply_count: int = 0
    retweet_count: int = 0
    target: str = ""

    @property
    def created_datetime(self) -> datetime:
        """Convert millisecond timestamp to datetime."""
        return datetime.fromtimestamp(self.created_at / 1000)

    @property
    def url(self) -> str:
        """Full URL to the article on xueqiu.com."""
        uid = self.user_id or (self.user.id if self.user else 0)
        return f"https://xueqiu.com/{uid}/{self.id}"


class ArticleListResponse(BaseModel):
    """Response from ``/statuses/original/timeline.json``."""

    model_config = {"populate_by_name": True}

    total: int = 0
    page: int = 1
    maxPage: int = 1
    articles: list[ArticleSummary] = Field(default_factory=builtins.list, alias="list")


class CommentUser(BaseModel):
    """User info embedded in comment responses."""

    id: int
    screen_name: str = ""


class Comment(BaseModel):
    """A single comment on an article.

    Author supplementary notes (补充说明) are comments where
    ``comment.user.id == article.user_id``.
    """

    id: int
    text: str = ""
    created_at: int = Field(
        default=0,
        description="Unix timestamp in milliseconds",
    )
    user: CommentUser | None = None
    like_count: int = 0

    @property
    def created_datetime(self) -> datetime:
        """Convert millisecond timestamp to datetime."""
        return datetime.fromtimestamp(self.created_at / 1000)


class CommentsResponse(BaseModel):
    """Response from ``/statuses/comments.json``."""

    count: int = 0
    page: int = 1
    maxPage: int = 1
    comments: list[Comment] = Field(default_factory=list)


class ArticleFull(BaseModel):
    """Full article data combining summary metadata and extracted content."""

    id: int
    title: str = ""
    content_html: str = ""
    content_markdown: str = ""
    created_at: int = 0
    user_id: int = 0
    view_count: int = 0
    like_count: int = 0
    reply_count: int = 0
    retweet_count: int = 0
    author_comments: list[Comment] = Field(default_factory=list)
    comments_fetch_failed: bool = False

    @property
    def created_datetime(self) -> datetime:
        """Convert millisecond timestamp to datetime."""
        return datetime.fromtimestamp(self.created_at / 1000)

    @property
    def url(self) -> str:
        """Full URL to the article on xueqiu.com."""
        return f"https://xueqiu.com/{self.user_id}/{self.id}"


class SyncManifestEntry(BaseModel):
    """Record of a successfully downloaded article."""

    article_id: int
    title: str = ""
    file_path: str = ""
    synced_at: str = ""
    comments_fetched: bool = True


class SyncManifest(BaseModel):
    """Tracks downloaded articles for incremental sync.

    Persisted as ``manifest.json`` in the data directory.
    """

    user_id: int = 0
    last_sync: str = ""
    articles: dict[str, SyncManifestEntry] = Field(default_factory=dict)

    def has_article(self, article_id: int) -> bool:
        """Check whether an article has already been downloaded."""
        return str(article_id) in self.articles

    def add_article(self, entry: SyncManifestEntry) -> None:
        """Register a newly downloaded article."""
        self.articles[str(entry.article_id)] = entry
