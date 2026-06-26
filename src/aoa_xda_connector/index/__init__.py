"""Tiny local keyword index for XDA starter data."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


TOKEN_RE = re.compile(r"[0-9A-Za-z]+(?:[._/\-][0-9A-Za-z]+)*")
FILE_IMAGE_STEMS = (
    "boot",
    "init_boot",
    "vendor_boot",
    "recovery",
    "vbmeta",
)
DEVICE_ALIAS_PATTERNS = (
    (re.compile(r"\bpixel\s+8\s+pro\b", re.I), "husky"),
)


def tokenize(text: str) -> list[str]:
    tokens = [token.lower() for token in TOKEN_RE.findall(text) if len(token) > 1]
    for alias in technical_alias_tokens(text):
        if alias not in tokens:
            tokens.append(alias)
    return tokens


def technical_alias_tokens(text: str) -> list[str]:
    aliases: list[str] = []
    lowered = text.lower()
    for stem in FILE_IMAGE_STEMS:
        pattern = re.escape(stem).replace("_", r"[\s_-]+")
        if re.search(rf"\b{pattern}[\s._-]+img\b", lowered):
            _append_unique(aliases, f"{stem}.img")
    for pattern, alias in DEVICE_ALIAS_PATTERNS:
        if pattern.search(text):
            _append_unique(aliases, alias)
    for match in re.finditer(r"\b[A-Z]{2,}\d?[A-Z0-9]*(?:\.[A-Z0-9]+){2,}\b", text):
        _append_unique(aliases, match.group(0).lower())
    return aliases


def extract_exact_terms(tokens: list[str]) -> list[str]:
    exact_terms: list[str] = []
    for token in tokens:
        if _is_exact_term(token) and token not in exact_terms:
            exact_terms.append(token)
    return exact_terms


def build_keyword_index(normalized_dir: Path, output_dir: Path, profile_id: str = "pixel-8-pro-husky") -> Path:
    docs: list[dict[str, object]] = []
    inverted: dict[str, list[dict[str, object]]] = defaultdict(list)
    exact: dict[str, list[str]] = defaultdict(list)
    for topic_path in sorted(normalized_dir.glob("topic-*.json")):
        topic = json.loads(topic_path.read_text(encoding="utf-8"))
        title = str(topic.get("title", ""))
        for post in topic.get("posts", []):
            text = str(post.get("text") or "")
            doc_id = f"post:{post.get('post_id')}"
            search_text = f"{title} {text}".strip()
            tokens = tokenize(search_text)
            counts = Counter(tokens)
            exact_terms = extract_exact_terms(tokens)
            docs.append(
                {
                    "doc_id": doc_id,
                    "topic_id": post.get("thread_id"),
                    "post_id": post.get("post_id"),
                    "source_url": post.get("source_url"),
                    "posted_at": post.get("posted_at"),
                    "captured_at": post.get("captured_at"),
                    "title": title,
                    "text": text,
                    "exact_text": " ".join(tokens),
                    "exact_terms": exact_terms,
                    "tokens": sum(counts.values()),
                }
            )
            for token, count in counts.items():
                inverted[token].append({"doc_id": doc_id, "count": count})
            for token in exact_terms:
                exact[token].append(doc_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "keyword_index.json"
    payload = {
        "schema": "aoa_xda_keyword_index_v1",
        "profile_id": profile_id,
        "unit": "post",
        "built_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "doc_count": len(docs),
        "term_count": len(inverted),
        "docs": docs,
        "inverted": inverted,
        "exact": exact,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _is_exact_term(token: str) -> bool:
    return any(char.isdigit() for char in token) or any(separator in token for separator in [".", "_", "/", "-"])


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
