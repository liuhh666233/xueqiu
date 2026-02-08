"""HTML content extraction and HTML-to-Markdown conversion for Xueqiu articles."""

import json
import re
import html as html_lib

from lxml import etree
from loguru import logger


# XPath for the main article content container.
ARTICLE_XPATH = '//div[contains(@class, "article__bd__detail")]'

# Regex to find the embedded JSON data in <script> tags.
SCRIPT_JSON_RE = re.compile(
    r'SNB\.data\.current_status\s*=\s*(\{.*?\})\s*;',
    re.DOTALL,
)


def extract_article_html(page_html: str) -> str:
    """Extract article body HTML from a full Xueqiu article page.

    Tries two strategies:
    1. XPath on the rendered HTML for the article detail div.
    2. Fallback: parse embedded JSON in ``<script>`` tags (Xueqiu uses
       client-side rendering so the content is often in JS data).

    Args:
        page_html: Full HTML source of the article page.

    Returns:
        Article body HTML, or empty string if extraction fails.
    """
    # Strategy 1: XPath on rendered HTML
    content = _extract_via_xpath(page_html)
    if content:
        return content

    # Strategy 2: Embedded JSON in script tags
    content = _extract_via_script_json(page_html)
    if content:
        return content

    logger.warning("Could not extract article content from HTML")
    return ""


def _extract_via_xpath(page_html: str) -> str:
    """Extract article HTML using XPath."""
    try:
        tree = etree.HTML(page_html)
        if tree is None:
            return ""

        nodes = tree.xpath(ARTICLE_XPATH)
        if not nodes:
            return ""

        # Serialize the first match back to HTML string
        return etree.tostring(nodes[0], encoding="unicode", method="html")
    except etree.Error:
        logger.debug("XPath extraction failed")
        return ""


def _extract_via_script_json(page_html: str) -> str:
    """Extract article content from embedded JSON in script tags."""
    match = SCRIPT_JSON_RE.search(page_html)
    if not match:
        return ""

    try:
        data = json.loads(match.group(1))
        # The content field contains the article HTML
        return data.get("text", "") or data.get("description", "")
    except (json.JSONDecodeError, KeyError):
        logger.debug("Script JSON extraction failed")
        return ""


def html_to_markdown(html_content: str) -> str:
    """Convert article HTML to Markdown.

    Handles common Xueqiu article elements: paragraphs, headings,
    links, images, bold/italic text, blockquotes, and lists.

    Args:
        html_content: Article body HTML.

    Returns:
        Markdown text.
    """
    if not html_content:
        return ""

    try:
        tree = etree.HTML(f"<div>{html_content}</div>")
    except etree.Error:
        # Fallback: strip all tags
        return _strip_tags(html_content)

    if tree is None:
        return _strip_tags(html_content)

    lines: list[str] = []
    body = tree.xpath("//div")[0] if tree.xpath("//div") else tree

    _walk_node(body, lines)

    text = "\n".join(lines)
    # Clean up excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _walk_node(node: etree._Element, lines: list[str]) -> None:
    """Recursively walk an HTML element tree, appending Markdown lines."""
    tag = _local_tag(node.tag) if isinstance(node.tag, str) else ""

    # Handle block-level elements
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(tag[1])
        text = _get_all_text(node).strip()
        if text:
            lines.append("")
            lines.append(f"{'#' * level} {text}")
            lines.append("")
        return

    if tag == "p":
        text = _inline_to_markdown(node).strip()
        if text:
            lines.append("")
            lines.append(text)
            lines.append("")
        return

    if tag == "br":
        lines.append("")
        return

    if tag == "blockquote":
        inner_lines: list[str] = []
        for child in node:
            _walk_node(child, inner_lines)
        text = _get_all_text(node).strip() if not inner_lines else "\n".join(inner_lines)
        for line in text.split("\n"):
            lines.append(f"> {line}")
        lines.append("")
        return

    if tag in ("ul", "ol"):
        lines.append("")
        for i, li in enumerate(node):
            if _local_tag(li.tag) == "li":
                text = _get_all_text(li).strip()
                prefix = f"{i + 1}." if tag == "ol" else "-"
                lines.append(f"{prefix} {text}")
        lines.append("")
        return

    if tag == "img":
        src = node.get("src", "")
        alt = node.get("alt", "")
        if src:
            # Fix protocol-relative URLs
            if src.startswith("//"):
                src = f"https:{src}"
            lines.append(f"![{alt}]({src})")
        return

    if tag == "hr":
        lines.append("")
        lines.append("---")
        lines.append("")
        return

    # For other tags (div, span, etc.), recurse into children
    if node.text:
        lines.append(node.text)

    for child in node:
        _walk_node(child, lines)
        if child.tail:
            lines.append(child.tail)


def _inline_to_markdown(node: etree._Element) -> str:
    """Convert inline HTML to Markdown (bold, italic, links, images)."""
    parts: list[str] = []

    if node.text:
        parts.append(node.text)

    for child in node:
        tag = _local_tag(child.tag) if isinstance(child.tag, str) else ""
        inner = _get_all_text(child).strip()

        if tag == "a":
            href = child.get("href", "")
            if href and inner:
                parts.append(f"[{inner}]({href})")
            elif inner:
                parts.append(inner)
        elif tag in ("strong", "b"):
            if inner:
                parts.append(f"**{inner}**")
        elif tag in ("em", "i"):
            if inner:
                parts.append(f"*{inner}*")
        elif tag == "img":
            src = child.get("src", "")
            alt = child.get("alt", "")
            if src:
                if src.startswith("//"):
                    src = f"https:{src}"
                parts.append(f"![{alt}]({src})")
        elif tag == "br":
            parts.append("\n")
        elif tag == "code":
            if inner:
                parts.append(f"`{inner}`")
        else:
            if inner:
                parts.append(inner)

        if child.tail:
            parts.append(child.tail)

    return "".join(parts)


def _get_all_text(node: etree._Element) -> str:
    """Get all text content from an element (including children)."""
    return etree.tostring(node, encoding="unicode", method="text") or ""


def _local_tag(tag: str) -> str:
    """Strip namespace prefix from tag name if present."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag.lower()


def _strip_tags(html_content: str) -> str:
    """Fallback: strip HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", "", html_content)
    return html_lib.unescape(text).strip()
