"""Operator-local XDA source registry and crawl planning."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path


SOURCE_KINDS = {"thread", "forum", "profile_seed"}
ACCESS_MODES = {"public", "account_visible"}
MEDIA_POLICIES = {"none", "thumbnails", "documents", "all"}
REGISTRY_SCHEMA = "aoa_xda_source_registry_v1"
SOURCE_SCHEMA = "aoa_xda_source_v1"
PLAN_SCHEMA = "aoa_xda_source_crawl_plan_v1"


def registry_path(data_root: Path) -> Path:
    return data_root / "sources" / "xda_sources.json"


def load_registry(data_root: Path) -> dict[str, object]:
    path = registry_path(data_root)
    if not path.exists():
        return {"schema": REGISTRY_SCHEMA, "sources": []}
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise ValueError(f"unsupported XDA source registry schema: {registry.get('schema')}")
    return registry


def save_registry(data_root: Path, registry: dict[str, object]) -> Path:
    path = registry_path(data_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")
    return path


def upsert_source(
    data_root: Path,
    *,
    source_ref: str,
    kind: str,
    access: str | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
    trust_score: float | None = None,
    include_media: str = "none",
    enabled: bool = True,
    scope: str | None = None,
) -> tuple[dict[str, object], Path, str]:
    source_ref = source_ref.strip()
    kind = kind.strip()
    access = access or "public"
    _validate(source_ref, kind, access, include_media, trust_score)
    registry = load_registry(data_root)
    sources = [source for source in registry.get("sources", []) if isinstance(source, dict)]
    source_id = _source_id(kind, source_ref)
    now = _now()
    existing = next((source for source in sources if source.get("source_id") == source_id), None)
    source = {
        "schema": SOURCE_SCHEMA,
        "source_id": source_id,
        "source_ref": source_ref,
        "route": f"xda:{kind}:{source_ref}",
        "kind": kind,
        "access": access,
        "title": title or (existing or {}).get("title") or source_ref,
        "scope": scope or (existing or {}).get("scope") or f"operator_selected_{kind}",
        "tags": _normalize_tags(tags or list((existing or {}).get("tags", []))),
        "trust_score": _trust_score(trust_score, existing),
        "enabled": bool(enabled),
        "operator_local": True,
        "read_only": True,
        "media_policy": {"include_media": include_media, "download_default": "disabled"},
        "source_receipt_required": True,
        "created_at": str((existing or {}).get("created_at") or now),
        "updated_at": now,
    }
    registry["sources"] = sorted([item for item in sources if item.get("source_id") != source_id] + [source], key=lambda item: str(item.get("source_id")))
    return source, save_registry(data_root, registry), "updated" if existing else "created"


def select_sources(registry: dict[str, object], *, source_refs: list[str] | None = None, kinds: list[str] | None = None, tags: list[str] | None = None, enabled_only: bool = True) -> list[dict[str, object]]:
    refs = {item.casefold() for item in source_refs or []}
    kind_filter = set(kinds or [])
    tag_filter = {item.casefold() for item in tags or []}
    selected = []
    for source in registry.get("sources", []):
        if not isinstance(source, dict):
            continue
        if enabled_only and not source.get("enabled", True):
            continue
        if refs and str(source.get("source_ref", "")).casefold() not in refs:
            continue
        if kind_filter and source.get("kind") not in kind_filter:
            continue
        source_tags = {str(tag).casefold() for tag in source.get("tags", [])}
        if tag_filter and not (tag_filter & source_tags):
            continue
        selected.append(source)
    return selected


def build_source_plan(*, run_id: str, sources: list[dict[str, object]], limit: int, include_media: str | None = None) -> dict[str, object]:
    steps = []
    for source in sources:
        media = include_media or dict(source.get("media_policy", {})).get("include_media") or "none"
        if media not in MEDIA_POLICIES:
            raise ValueError(f"unsupported media policy: {media}")
        steps.append(
            {
                "source_id": source.get("source_id"),
                "source_ref": source.get("source_ref"),
                "kind": source.get("kind"),
                "access": source.get("access"),
                "scope": source.get("scope"),
                "tags": source.get("tags", []),
                "trust_score": source.get("trust_score"),
                "max_pages": limit,
                "include_media": media,
                "operation": "crawl",
                "network_touched": False,
                "read_only": True,
                "download_touched": False,
            }
        )
    return {"schema": PLAN_SCHEMA, "run_id": run_id, "selected_count": len(steps), "steps": steps, "network_touched": False, "read_only": True, "download_touched": False, "created_at": _now()}


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _validate(source_ref: str, kind: str, access: str, include_media: str, trust_score: float | None) -> None:
    if not source_ref:
        raise ValueError("source_ref is required")
    if kind not in SOURCE_KINDS:
        raise ValueError(f"unsupported XDA source kind: {kind}")
    if access not in ACCESS_MODES:
        raise ValueError(f"unsupported XDA access mode: {access}")
    if include_media not in MEDIA_POLICIES:
        raise ValueError(f"unsupported media policy: {include_media}")
    if trust_score is not None and not 0 <= trust_score <= 1:
        raise ValueError("trust_score must be between 0 and 1")


def _source_id(kind: str, source_ref: str) -> str:
    digest = hashlib.sha256(f"{kind}:{source_ref.casefold()}".encode("utf-8")).hexdigest()
    return f"xda-src-{digest[:16]}"


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized = []
    seen = set()
    for tag in tags:
        item = re.sub(r"\s+", "-", str(tag).strip().casefold())
        if item and item not in seen:
            seen.add(item)
            normalized.append(item)
    return normalized


def _trust_score(value: float | None, existing: dict[str, object] | None) -> float:
    if value is not None:
        return round(float(value), 3)
    existing_value = (existing or {}).get("trust_score")
    return round(float(existing_value), 3) if isinstance(existing_value, int | float) else 0.5


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
