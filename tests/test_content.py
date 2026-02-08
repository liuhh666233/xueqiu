"""Tests for scraper.content."""

import unittest
from pathlib import Path

from scraper.content import extract_article_html, html_to_markdown

FIXTURES = Path(__file__).parent / "fixtures"


class TestExtractArticleHtml(unittest.TestCase):
    """Test HTML content extraction from article pages."""

    def setUp(self) -> None:
        self.page_html = (FIXTURES / "article_page.html").read_text()

    def test_extracts_content(self) -> None:
        html = extract_article_html(self.page_html)
        self.assertIn("第一段内容", html)
        self.assertIn("加粗", html)

    def test_extracts_via_xpath(self) -> None:
        html = extract_article_html(self.page_html)
        self.assertNotEqual(html, "")

    def test_empty_input(self) -> None:
        html = extract_article_html("")
        self.assertEqual(html, "")

    def test_no_article_div(self) -> None:
        html = extract_article_html("<html><body><p>nothing</p></body></html>")
        self.assertEqual(html, "")


class TestExtractViaScriptJson(unittest.TestCase):
    """Test extraction from embedded script JSON."""

    def test_script_json_extraction(self) -> None:
        page = '''
        <html><body>
        <script>
        SNB.data.current_status = {"text": "<p>脚本中的内容</p>", "id": 123};
        </script>
        </body></html>
        '''
        html = extract_article_html(page)
        self.assertIn("脚本中的内容", html)


class TestHtmlToMarkdown(unittest.TestCase):
    """Test HTML-to-Markdown conversion."""

    def test_paragraph(self) -> None:
        md = html_to_markdown("<p>Hello world</p>")
        self.assertIn("Hello world", md)

    def test_heading(self) -> None:
        md = html_to_markdown("<h2>标题</h2>")
        self.assertIn("## 标题", md)

    def test_bold(self) -> None:
        md = html_to_markdown("<p><strong>粗体</strong></p>")
        self.assertIn("**粗体**", md)

    def test_link(self) -> None:
        md = html_to_markdown('<p><a href="https://example.com">链接</a></p>')
        self.assertIn("[链接](https://example.com)", md)

    def test_image_protocol_relative(self) -> None:
        md = html_to_markdown('<img src="//xqimg.imedao.com/test.jpg" alt="图片"/>')
        self.assertIn("![图片](https://xqimg.imedao.com/test.jpg)", md)

    def test_unordered_list(self) -> None:
        md = html_to_markdown("<ul><li>一</li><li>二</li></ul>")
        self.assertIn("- 一", md)
        self.assertIn("- 二", md)

    def test_blockquote(self) -> None:
        md = html_to_markdown("<blockquote>引用内容</blockquote>")
        self.assertIn("> ", md)
        self.assertIn("引用内容", md)

    def test_empty_input(self) -> None:
        md = html_to_markdown("")
        self.assertEqual(md, "")

    def test_full_article_page(self) -> None:
        page_html = (FIXTURES / "article_page.html").read_text()
        content_html = extract_article_html(page_html)
        md = html_to_markdown(content_html)
        self.assertIn("小标题", md)
        self.assertIn("第一段内容", md)
        self.assertIn("列表项一", md)


if __name__ == "__main__":
    unittest.main()
