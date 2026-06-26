"""Normalize public-safe XDA snapshots into topic/post records."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from aoa_xda_connector.parse import decode_html, extract_posts, extract_thread_id, extract_title


FILE_RE = re.compile(r"\b[\w.-]+\.(?:img|zip|apk|bin|tar|tgz|xz)\b", re.I)
PARTITION_IMAGE_RE = re.compile(r"\b(?:boot|init_boot|vendor_boot|recovery|dtbo|vbmeta|super)(?:-[a-z0-9_]+)?\.img\b", re.I)
ANDROID_VERSION_RE = re.compile(r"\bAndroid\s+\d+(?:\.\d+)?\b", re.I)
BUILD_ID_RE = re.compile(r"\b[A-Z]{2,}\d?[A-Z0-9]*(?:\.[A-Z0-9]+){2,}\b")
DEVICE_RE = re.compile(r"\b(?:Pixel\s+8\s+Pro|Pixel\s+8|Pixel\s+7\s+Pro|OnePlus\s+12)\b", re.I)
KNOWN_TOOLS = {
    "adb": "ADB",
    "fastboot": "fastboot",
    "kernelsu": "KernelSU",
    "kernel su": "KernelSU",
    "ksu": "KernelSU",
    "magisk canary": "Magisk Canary",
    "magisk": "Magisk",
    "orangefox": "OrangeFox",
    "orange fox": "OrangeFox",
    "twrp": "TWRP",
}
KNOWN_CODENAMES = {
    "husky",
    "cheetah",
    "panther",
    "akita",
    "waffle",
}
FIRMWARE_FAMILIES = {
    "aosp": "AOSP",
    "lineageos": "LineageOS",
    "oxygenos": "OxygenOS",
    "factory image": "factory image",
}
RISK_TERMS = {
    "bootloop": "bootloop",
    "brick": "brick",
    "data loss": "data_loss",
    "wipe": "data_wipe",
}


def normalize_snapshot(raw_path: Path, source_url: str, output_dir: Path) -> Path:
    document = decode_html(raw_path.read_bytes())
    captured_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    thread_id = extract_thread_id(source_url)
    title = extract_title(document)
    posts = []
    for post in extract_posts(document, source_url):
        post_id = str(post["post_id"])
        text = str(post["text"])
        posts.append(
            {
                "schema": "aoa_xda_normalized_post_v1",
                "post_id": post_id,
                "thread_id": thread_id,
                "source_url": f"{source_url.rstrip('/')}#post-{post_id}",
                "author_label": post.get("author_label"),
                "posted_at": post.get("posted_at"),
                "captured_at": captured_at,
                "text": text,
                "quote_policy": post.get("quote_policy"),
                "code_excerpts": post.get("code_excerpts", []),
                "link_excerpts": post.get("link_excerpts", []),
                "entities": extract_entities(text),
            }
        )
    topic = {
        "schema": "aoa_xda_normalized_topic_v1",
        "thread_id": thread_id,
        "source_url": source_url,
        "title": title,
        "captured_at": captured_at,
        "posts": posts,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"topic-{thread_id}-page1.json"
    output_path.write_text(json.dumps(topic, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def extract_entities(text: str) -> list[dict[str, str]]:
    entities: list[dict[str, str]] = []
    lowered = text.casefold()
    for match in DEVICE_RE.finditer(text):
        _add_entity(entities, "device", _canonical_spaces(match.group(0)))
    for codename in KNOWN_CODENAMES:
        if re.search(rf"\b{re.escape(codename)}\b", lowered):
            _add_entity(entities, "codename", codename)
    for match in ANDROID_VERSION_RE.finditer(text):
        _add_entity(entities, "android_version", _canonical_spaces(match.group(0)))
    for match in BUILD_ID_RE.finditer(text):
        _add_entity(entities, "build_id", match.group(0).upper())
    for raw, canonical in FIRMWARE_FAMILIES.items():
        if re.search(rf"\b{re.escape(raw)}\b", lowered):
            _add_entity(entities, "firmware_family", canonical)
    for raw, canonical in KNOWN_TOOLS.items():
        if re.search(rf"\b{re.escape(raw)}\b", lowered):
            _add_entity(entities, "tool", canonical)
    for match in FILE_RE.finditer(text):
        _add_entity(entities, "file", match.group(0).lower())
    for match in PARTITION_IMAGE_RE.finditer(text):
        _add_entity(entities, "file", match.group(0).lower())
    for raw, canonical in RISK_TERMS.items():
        if raw in lowered:
            _add_entity(entities, "risk", canonical)

    _add_conditions(entities, lowered)
    _add_actions(entities, lowered)
    _add_warning_entities(entities, lowered)
    _add_status_entities(entities, text, lowered)
    return entities


def _add_conditions(entities: list[dict[str, str]], lowered: str) -> None:
    if "bootloader" in lowered and ("unlock" in lowered or "unlocked" in lowered):
        _add_entity(entities, "condition", "bootloader_unlocked")
    if "matching" in lowered or "same build" in lowered or "current factory image" in lowered:
        _add_entity(entities, "condition", "matching_build")
    if "manual review" in lowered or "not confirmed" in lowered:
        _add_entity(entities, "condition", "manual_review_required")


def _add_actions(entities: list[dict[str, str]], lowered: str) -> None:
    files = {entity["value"] for entity in entities if entity["kind"] == "file"}
    for file_value in sorted(files):
        file_pattern = re.escape(file_value)
        if file_value in {"boot.img", "init_boot.img"} and (
            re.search(rf"\b(?:patch|patching|patched|re-patch)\b[^.?!]{{0,120}}{file_pattern}", lowered)
            or re.search(rf"{file_pattern}.{{0,120}}\b(?:magisk|kernelsu|ksu)\b", lowered)
        ):
            _add_entity(entities, "root_action", f"patch {file_value}")
        if file_value in {"recovery.img", "vendor_boot.img"} and (
            re.search(rf"\b(?:flash|flashing)\b[^.?!]{{0,120}}{file_pattern}", lowered)
            or re.search(rf"{file_pattern}.{{0,120}}\b(?:fastboot|twrp|orangefox|orange\s+fox)\b", lowered)
        ):
            _add_entity(entities, "recovery_action", f"flash {file_value}")


def _add_warning_entities(entities: list[dict[str, str]], lowered: str) -> None:
    has_warning = any(term in lowered for term in ["warning", "do not", "don't", "caused", "risk", "bootloop", "data loss", "brick"])
    if not has_warning:
        return
    files = [entity["value"] for entity in entities if entity["kind"] == "file"]
    risks = [entity["value"] for entity in entities if entity["kind"] == "risk"]
    if files:
        _add_entity(entities, "warning", f"do not flash {'/'.join(files)} without matching build")
    elif risks:
        _add_entity(entities, "warning", f"risk of {'/'.join(risks)}")


def _add_status_entities(entities: list[dict[str, str]], text: str, lowered: str) -> None:
    if any(term in lowered for term in ["no longer", "stale", "old patched", "supersedes", "current method", "after the june ota"]):
        _add_entity(entities, "status", _status_excerpt(text))


def _status_excerpt(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        if "supersedes" in sentence.casefold():
            return sentence[:180]
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        lowered = sentence.casefold()
        if any(term in lowered for term in ["no longer", "stale", "supersedes", "current method"]):
            return sentence[:180]
    return text[:180]


def _add_entity(entities: list[dict[str, str]], kind: str, value: str) -> None:
    canonical = _canonical_spaces(value)
    if not canonical:
        return
    if any(entity["kind"] == kind and entity["value"].casefold() == canonical.casefold() for entity in entities):
        return
    entities.append({"kind": kind, "value": canonical})


def _canonical_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
