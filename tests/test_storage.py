"""Tests for scraper.storage."""

import json
import tempfile
import unittest
from pathlib import Path

from scraper.models import ArticleFull, Comment, CommentUser, SyncManifest, SyncManifestEntry
from scraper.storage import (
    build_article_path,
    load_manifest,
    sanitize_filename,
    save_article,
    save_manifest,
)


class TestSanitizeFilename(unittest.TestCase):
    """Test filename sanitization."""

    def test_basic(self) -> None:
        self.assertEqual(sanitize_filename("Hello World"), "Hello_World")

    def test_chinese(self) -> None:
        result = sanitize_filename("测试文章标题")
        self.assertEqual(result, "测试文章标题")

    def test_special_chars(self) -> None:
        result = sanitize_filename("a/b\\c:d?e*f")
        self.assertNotIn("/", result)
        self.assertNotIn("\\", result)

    def test_truncation(self) -> None:
        long_name = "a" * 100
        result = sanitize_filename(long_name, max_length=20)
        self.assertLessEqual(len(result), 20)

    def test_empty(self) -> None:
        self.assertEqual(sanitize_filename(""), "untitled")

    def test_only_special(self) -> None:
        self.assertEqual(sanitize_filename("///"), "untitled")


class TestBuildArticlePath(unittest.TestCase):
    """Test article file path construction."""

    def test_path_format(self) -> None:
        article = ArticleFull(
            id=123456,
            title="测试文章",
            created_at=1705276200000,  # 2024-01-15
            user_id=2426670165,
        )
        path = build_article_path(Path("data/articles"), article)
        self.assertIn("2024", str(path))
        self.assertIn("2024-01-1", str(path))
        self.assertIn("测试文章", str(path))
        self.assertIn("123456", str(path))
        self.assertTrue(str(path).endswith(".md"))


class TestSaveArticle(unittest.TestCase):
    """Test saving articles to disk."""

    def test_save_creates_file(self) -> None:
        article = ArticleFull(
            id=123456,
            title="测试文章",
            content_markdown="这是内容",
            created_at=1705276200000,
            user_id=2426670165,
            view_count=100,
            like_count=10,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_article(Path(tmpdir), article)
            self.assertTrue(path.exists())

            content = path.read_text(encoding="utf-8")
            self.assertIn("---", content)
            self.assertIn("title:", content)
            self.assertIn("测试文章", content)
            self.assertIn("这是内容", content)
            self.assertIn("article_id: 123456", content)

    def test_save_with_author_comments(self) -> None:
        article = ArticleFull(
            id=123456,
            title="带补充的文章",
            content_markdown="正文内容",
            created_at=1705276200000,
            user_id=2426670165,
            author_comments=[
                Comment(
                    id=1,
                    text="补充说明一",
                    created_at=1705362600000,
                    user=CommentUser(id=2426670165, screen_name="作者"),
                ),
                Comment(
                    id=2,
                    text="补充说明二",
                    created_at=1705449000000,
                    user=CommentUser(id=2426670165, screen_name="作者"),
                ),
            ],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_article(Path(tmpdir), article)
            content = path.read_text(encoding="utf-8")
            self.assertIn("## 补充说明", content)
            self.assertIn("补充说明一", content)
            self.assertIn("补充说明二", content)


class TestManifestPersistence(unittest.TestCase):
    """Test manifest save/load round-trip."""

    def test_save_and_load(self) -> None:
        manifest = SyncManifest(user_id=12345)
        manifest.add_article(
            SyncManifestEntry(
                article_id=999,
                title="Test Article",
                file_path="data/2024/test.md",
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            save_manifest(data_dir, manifest)
            loaded = load_manifest(data_dir)

            self.assertEqual(loaded.user_id, 12345)
            self.assertTrue(loaded.has_article(999))
            self.assertNotEqual(loaded.last_sync, "")

    def test_load_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = load_manifest(Path(tmpdir))
            self.assertEqual(len(manifest.articles), 0)

    def test_load_corrupted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            (data_dir / "manifest.json").write_text("not valid json")
            manifest = load_manifest(data_dir)
            self.assertEqual(len(manifest.articles), 0)


if __name__ == "__main__":
    unittest.main()
