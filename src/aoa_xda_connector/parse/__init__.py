"""Small HTML parsing helpers for public XDA thread snapshots."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import urljoin


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
ARTICLE_RE = re.compile(r"<article\b([^>]*)>(.*?)</article>", re.I | re.S)
POST_ID_RE = re.compile(r"(?:id|data-content)=['\"]post-(\d+)['\"]", re.I)
TIME_RE = re.compile(r"<time[^>]+datetime=['\"]([^'\"]+)['\"][^>]*>", re.I | re.S)
AUTHOR_RE = re.compile(r"class=['\"][^'\"]*username[^'\"]*['\"][^>]*>(.*?)</a>", re.I | re.S)
BODY_RE = re.compile(r"<div[^>]+class=['\"][^'\"]*bbWrapper[^'\"]*['\"][^>]*>(.*?)</div>\s*</div>", re.I | re.S)
CODE_RE = re.compile(r"<code[^>]*>(.*?)</code>|<pre[^>]*>(.*?)</pre>", re.I | re.S)
LINK_RE = re.compile(r"<a[^>]+href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", re.I | re.S)
QUOTE_BLOCK_RE = re.compile(
    r"<(?:blockquote|div)[^>]+class=['\"][^'\"]*(?:quote|bbCodeBlock--quote)[^'\"]*['\"][^>]*>.*?</(?:blockquote|div)>",
    re.I | re.S,
)
SIGNATURE_RE = re.compile(r"<aside[^>]+class=['\"][^'\"]*signature[^'\"]*['\"][^>]*>.*?</aside>", re.I | re.S)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key.lower(): value or "" for key, value in attrs}
        class_attr = attrs_map.get("class", "").lower()
        if self.skip_depth or tag.lower() in {"script", "style"} or "message-signature" in class_attr:
            self.skip_depth += 1

    def handle_endtag(self, _tag: str) -> None:
        if self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self) -> str:
        return " ".join(self.parts)


def decode_html(data: bytes) -> str:
    for encoding in ["utf-8", "windows-1251"]:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def extract_title(document: str) -> str:
    h1_match = H1_RE.search(document)
    if h1_match:
        return clean_text(h1_match.group(1))
    title_match = TITLE_RE.search(document)
    return clean_text(title_match.group(1)) if title_match else "Untitled XDA thread"


def extract_thread_id(source_url: str) -> str:
    match = re.search(r"\.(\d+)(?:/|$)", source_url)
    if match:
        return match.group(1)
    return "fixture-thread"


def extract_posts(document: str, source_url: str) -> list[dict[str, object]]:
    posts: list[dict[str, object]] = []
    for attrs, block in ARTICLE_RE.findall(document):
        post_id_match = POST_ID_RE.search(attrs) or POST_ID_RE.search(block)
        if not post_id_match:
            continue
        post_id = post_id_match.group(1)
        body = _extract_body(block)
        body_without_quotes = _strip_non_evidence_blocks(body)
        text = clean_text(body_without_quotes)
        if not text:
            continue
        posts.append(
            {
                "post_id": post_id,
                "author_label": _extract_optional(AUTHOR_RE, block),
                "posted_at": _extract_optional(TIME_RE, block),
                "text": text[:12000],
                "code_excerpts": _code_excerpts(body_without_quotes),
                "link_excerpts": _link_excerpts(body_without_quotes, source_url),
                "quote_policy": "quote_blocks_stripped",
            }
        )
    return posts


def clean_text(fragment: str) -> str:
    extractor = TextExtractor()
    extractor.feed(fragment)
    text = html.unescape(extractor.get_text())
    return re.sub(r"\s+", " ", text).strip()


def _extract_body(block: str) -> str:
    match = BODY_RE.search(block)
    return match.group(1) if match else block


def _strip_non_evidence_blocks(block: str) -> str:
    block = QUOTE_BLOCK_RE.sub(" ", block)
    block = SIGNATURE_RE.sub(" ", block)
    return block


def _extract_optional(pattern: re.Pattern[str], block: str) -> str | None:
    match = pattern.search(block)
    return clean_text(match.group(1)) if match else None


def _code_excerpts(block: str) -> list[str]:
    excerpts: list[str] = []
    for left, right in CODE_RE.findall(block):
        text = clean_text(left or right)
        if text and text not in excerpts:
            excerpts.append(text)
    return excerpts


def _link_excerpts(block: str, source_url: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for href, label in LINK_RE.findall(block):
        absolute = urljoin(source_url, html.unescape(href))
        text = clean_text(label)
        if absolute:
            links.append({"url": absolute, "label": text})
    return links
