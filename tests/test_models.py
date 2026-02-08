"""Tests for scraper.models."""

import json
import unittest
from pathlib import Path

from scraper.models import (
    ArticleListResponse,
    ArticleSummary,
    Comment,
    CommentsResponse,
    SyncManifest,
    SyncManifestEntry,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestArticleListResponse(unittest.TestCase):
    """Test parsing of article list API responses."""

    def setUp(self) -> None:
        raw = json.loads((FIXTURES / "article_list.json").read_text())
        self.response = ArticleListResponse.model_validate(raw)

    def test_total(self) -> None:
        self.assertEqual(self.response.total, 2)

    def test_max_page(self) -> None:
        self.assertEqual(self.response.maxPage, 1)

    def test_article_count(self) -> None:
        self.assertEqual(len(self.response.articles), 2)

    def test_article_fields(self) -> None:
        article = self.response.articles[0]
        self.assertEqual(article.id, 300000001)
        self.assertEqual(article.title, "测试文章标题一")
        self.assertEqual(article.user_id, 2426670165)
        self.assertEqual(article.view_count, 1500)

    def test_article_url(self) -> None:
        article = self.response.articles[0]
        self.assertEqual(article.url, "https://xueqiu.com/2426670165/300000001")

    def test_created_datetime(self) -> None:
        article = self.response.articles[0]
        dt = article.created_datetime
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 1)


class TestCommentsResponse(unittest.TestCase):
    """Test parsing of comments API responses."""

    def setUp(self) -> None:
        raw = json.loads((FIXTURES / "comments.json").read_text())
        self.response = CommentsResponse.model_validate(raw)

    def test_comment_count(self) -> None:
        self.assertEqual(self.response.count, 3)

    def test_comments_parsed(self) -> None:
        self.assertEqual(len(self.response.comments), 3)

    def test_comment_user(self) -> None:
        comment = self.response.comments[0]
        self.assertIsNotNone(comment.user)
        self.assertEqual(comment.user.id, 2426670165)

    def test_filter_author_comments(self) -> None:
        author_id = 2426670165
        author_comments = [
            c for c in self.response.comments
            if c.user and c.user.id == author_id
        ]
        self.assertEqual(len(author_comments), 2)


class TestSyncManifest(unittest.TestCase):
    """Test sync manifest operations."""

    def test_empty_manifest(self) -> None:
        manifest = SyncManifest()
        self.assertFalse(manifest.has_article(123))
        self.assertEqual(len(manifest.articles), 0)

    def test_add_and_check(self) -> None:
        manifest = SyncManifest()
        entry = SyncManifestEntry(
            article_id=123,
            title="Test",
            file_path="data/2024/test.md",
            synced_at="2024-01-15T10:00:00+08:00",
        )
        manifest.add_article(entry)
        self.assertTrue(manifest.has_article(123))
        self.assertFalse(manifest.has_article(456))

    def test_roundtrip_json(self) -> None:
        manifest = SyncManifest(user_id=12345)
        entry = SyncManifestEntry(
            article_id=999,
            title="Round trip",
            file_path="data/test.md",
        )
        manifest.add_article(entry)

        json_str = manifest.model_dump_json()
        restored = SyncManifest.model_validate_json(json_str)

        self.assertEqual(restored.user_id, 12345)
        self.assertTrue(restored.has_article(999))


if __name__ == "__main__":
    unittest.main()
