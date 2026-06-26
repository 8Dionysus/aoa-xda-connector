"""Portable claim extraction primitives for XDA forum evidence."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime


CLAIM_EXTRACTOR_VERSION = "xda_claim_heuristic_v1"
RELATION_EXTRACTOR_VERSION = "connector_claim_relation_v1"
CLAIM_RELATION_KINDS = {
    "claim_applies_to_context",
    "method_uses_tool",
    "method_targets_object",
    "method_requires_condition",
    "warning_targets_action",
    "warning_targets_object",
    "claim_contextualizes_claim",
    "claim_supersedes_claim",
    "claim_contradicts_claim",
    "claim_deprecated_for_context",
    "source_supports_claim",
    "source_warns_about_claim",
    "source_updates_claim",
    "claim_confirms_claim",
    "claim_refines_claim",
    "claim_scope_limited_by",
    "claim_unknown_for_context",
    "claim_requires_manual_review",
}


def extract_post_claims(post: dict[str, object], profile_id: str) -> list[dict[str, object]]:
    text = str(post.get("text") or "")
    lowered = text.casefold()
    entities = [entity for entity in post.get("entities", []) if isinstance(entity, dict)]
    claims: list[dict[str, object]] = []

    context_labels = _context_labels(entities)
    condition_labels = _labels_by_kind(entities, "condition")
    risk_labels = _labels_by_kind(entities, "risk")
    warning_labels = _labels_by_kind(entities, "warning")
    manual_review = "manual review" in lowered or "not confirmed" in lowered

    for action in _entities_by_kind(entities, "root_action"):
        action_label = str(action.get("value") or "")
        claims.append(
            _claim(
                post,
                profile_id,
                claim_kind="method",
                method_kind="root",
                action_label=action_label,
                target_labels=_targets_for_action(action_label, entities),
                tool_labels=_tool_labels(entities, {"Magisk", "Magisk Canary", "KernelSU", "fastboot"}),
                context_labels=context_labels,
                condition_labels=condition_labels,
                risk_labels=risk_labels,
                warning_labels=warning_labels,
                confidence=0.76,
                extraction_rule="xda_root_action_entity_v1",
                manual_review_required=manual_review,
                evidence_span=_evidence_span(text, action_label),
            )
        )

    for action in _entities_by_kind(entities, "recovery_action"):
        action_label = str(action.get("value") or "")
        claims.append(
            _claim(
                post,
                profile_id,
                claim_kind="method",
                method_kind="recovery",
                action_label=action_label,
                target_labels=_targets_for_action(action_label, entities),
                tool_labels=_tool_labels(entities, {"fastboot", "TWRP", "OrangeFox"}),
                context_labels=context_labels,
                condition_labels=condition_labels,
                risk_labels=risk_labels,
                warning_labels=warning_labels,
                confidence=0.68,
                extraction_rule="xda_recovery_action_entity_v1",
                manual_review_required=manual_review,
                evidence_span=_evidence_span(text, action_label),
            )
        )

    for warning in _entities_by_kind(entities, "warning"):
        warning_label = str(warning.get("value") or "")
        claims.append(
            _claim(
                post,
                profile_id,
                claim_kind="warning",
                method_kind="risk_warning",
                action_label=warning_label,
                target_labels=_warning_target_labels(warning_label, entities),
                tool_labels=_tool_labels(entities),
                context_labels=context_labels,
                condition_labels=condition_labels,
                risk_labels=risk_labels or ["unsafe_without_matching_context"],
                warning_labels=[warning_label],
                confidence=0.72,
                extraction_rule="xda_warning_entity_v1",
                manual_review_required=manual_review,
                evidence_span=_evidence_span(text, warning_label),
            )
        )

    for status in _entities_by_kind(entities, "status"):
        status_label = str(status.get("value") or "")
        claims.append(
            _claim(
                post,
                profile_id,
                claim_kind="status",
                method_kind="freshness_update",
                action_label=status_label,
                target_labels=_labels_by_kind(entities, "file") + _labels_by_kind(entities, "build_id"),
                tool_labels=_tool_labels(entities),
                context_labels=context_labels,
                condition_labels=condition_labels,
                risk_labels=risk_labels,
                warning_labels=[],
                confidence=0.62,
                extraction_rule="xda_status_language_v1",
                manual_review_required=True,
                evidence_span=_evidence_span(text, status_label),
            )
        )

    return _dedupe_claims(claims)


def assign_freshness_windows(claims: list[dict[str, object]]) -> None:
    if not claims:
        return
    ranked = sorted(claims, key=lambda claim: (_claim_time_sort_key(claim), str(claim.get("claim_id"))))
    related_by_key: dict[str, list[dict[str, object]]] = {}
    for claim in ranked:
        related_by_key.setdefault(_relation_key(claim), []).append(claim)
    count = len(ranked)
    for index, claim in enumerate(ranked):
        freshness = claim.setdefault("freshness_context", {})
        if not isinstance(freshness, dict):
            freshness = {}
            claim["freshness_context"] = freshness
        if count == 1 or index == count - 1:
            window = "latest_window"
        elif index < count / 3:
            window = "early"
        elif index < (2 * count) / 3:
            window = "middle"
        else:
            window = "late"
        newer_related = [
            str(other.get("claim_id"))
            for other in related_by_key.get(_relation_key(claim), [])
            if _claim_time_sort_key(other) > _claim_time_sort_key(claim)
        ]
        freshness["profile_window"] = window
        freshness["newer_related_claim_ids"] = newer_related
        freshness["newer_related_claims_exist"] = bool(newer_related)
        freshness["possibly_superseded"] = bool(newer_related)


def graph_nodes_for_claims(claims: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    nodes: dict[str, dict[str, object]] = {}
    for claim in claims:
        claim_id = str(claim["claim_id"])
        source_url = str(claim.get("source_url") or "")
        nodes[claim_id] = {
            "schema": "aoa_connector_claim_node_v1",
            "node_id": claim_id,
            "kind": "claim",
            "label": str(claim.get("label") or claim.get("action") or claim_id),
            "source_refs": [source_url] if source_url else [],
            "confidence": float(claim.get("confidence") or 0.0),
            "claim": claim,
        }
        method_id = str(claim.get("method_id") or "")
        if method_id:
            _upsert_node(nodes, method_id, "method", str(claim.get("method_label") or method_id), source_url, 0.65)
        action_node = _action_node_id(claim.get("action"))
        if action_node:
            _upsert_node(nodes, action_node, "action", str(claim.get("action")), source_url, 0.65)
        for label in _strings(claim.get("target_labels", [])):
            _upsert_node(nodes, _target_node_id(label), "target", label, source_url, 0.65)
        for label in _strings(claim.get("tool_labels", [])):
            _upsert_node(nodes, _tool_node_id(label), "tool", label, source_url, 0.65)
        for label in _strings(claim.get("condition_labels", [])):
            _upsert_node(nodes, _condition_node_id(label), "condition", label, source_url, 0.6)
        for label in _strings(claim.get("applicability_context", [])):
            _upsert_node(nodes, _context_node_id(label), "applicability_context", label, source_url, 0.6)
        for label in _strings(claim.get("warning_labels", [])):
            _upsert_node(nodes, _warning_node_id(label), "warning", label, source_url, 0.65)
    return nodes


def relation_edges_for_claims(claims: list[dict[str, object]]) -> list[dict[str, object]]:
    edges: list[dict[str, object]] = []
    for claim in claims:
        claim_id = str(claim["claim_id"])
        post_node = f"post:{claim.get('source_post_id')}"
        source_kind = "source_warns_about_claim" if claim.get("claim_kind") == "warning" else "source_supports_claim"
        _append_claim_edge(edges, source_kind, post_node, claim_id, claim, confidence=float(claim.get("confidence") or 0.0))
        if claim.get("claim_kind") == "status":
            _append_claim_edge(edges, "source_updates_claim", post_node, claim_id, claim, confidence=0.55)
        method_id = str(claim.get("method_id") or "")
        action_node = _action_node_id(claim.get("action"))
        if action_node:
            _append_claim_edge(edges, "claim_applies_to_context", claim_id, action_node, claim, confidence=0.55)
        if method_id:
            _append_claim_edge(edges, "claim_refines_claim", claim_id, method_id, claim, confidence=0.45)
            for label in _strings(claim.get("tool_labels", [])):
                _append_claim_edge(edges, "method_uses_tool", method_id, _tool_node_id(label), claim, confidence=0.6)
            for label in _strings(claim.get("target_labels", [])):
                _append_claim_edge(edges, "method_targets_object", method_id, _target_node_id(label), claim, confidence=0.65)
            for label in _strings(claim.get("condition_labels", [])):
                _append_claim_edge(edges, "method_requires_condition", method_id, _condition_node_id(label), claim, confidence=0.5)
        for label in _strings(claim.get("applicability_context", [])):
            _append_claim_edge(edges, "claim_applies_to_context", claim_id, _context_node_id(label), claim, confidence=0.55)
        if claim.get("claim_kind") == "warning":
            for label in _strings(claim.get("target_labels", [])):
                _append_claim_edge(edges, "warning_targets_object", claim_id, _target_node_id(label), claim, confidence=0.62)
            if action_node:
                _append_claim_edge(edges, "warning_targets_action", claim_id, action_node, claim, confidence=0.55)
    _append_cross_claim_edges(edges, claims)
    return edges


def claim_graph_stats(claims: list[dict[str, object]], edges: list[dict[str, object]]) -> dict[str, object]:
    relation_counts: dict[str, int] = {}
    for edge in edges:
        kind = str(edge.get("kind") or "")
        if kind in CLAIM_RELATION_KINDS:
            relation_counts[kind] = relation_counts.get(kind, 0) + 1
    return {
        "schema": "aoa_connector_claim_graph_stats_v1",
        "claim_count": len(claims),
        "method_count": sum(1 for claim in claims if claim.get("claim_kind") == "method"),
        "warning_count": sum(1 for claim in claims if claim.get("claim_kind") == "warning"),
        "status_count": sum(1 for claim in claims if claim.get("claim_kind") == "status"),
        "relation_counts": relation_counts,
        "supersedes_count": relation_counts.get("claim_supersedes_claim", 0),
        "contradicts_count": relation_counts.get("claim_contradicts_claim", 0),
        "contextualizes_count": relation_counts.get("claim_contextualizes_claim", 0),
    }


def _claim(
    post: dict[str, object],
    profile_id: str,
    *,
    claim_kind: str,
    method_kind: str,
    action_label: str,
    target_labels: list[str],
    tool_labels: list[str],
    context_labels: list[str],
    condition_labels: list[str],
    risk_labels: list[str],
    warning_labels: list[str],
    confidence: float,
    extraction_rule: str,
    manual_review_required: bool,
    evidence_span: dict[str, object],
) -> dict[str, object]:
    label = _claim_label(action_label, target_labels, tool_labels, context_labels)
    post_id = str(post.get("post_id") or "unknown")
    method_id = f"method:{profile_id}:{_slug(method_kind)}:{_slug(label)}" if claim_kind == "method" else None
    claim_id = f"claim:{profile_id}:{post_id}:{_slug(claim_kind)}:{_slug(label)}"
    if len(claim_id) > 150:
        claim_id = f"claim:{profile_id}:{post_id}:{_slug(claim_kind)}:{hashlib.sha256(label.encode('utf-8')).hexdigest()[:16]}"
    source_post = {
        "post_id": post.get("post_id"),
        "thread_id": post.get("thread_id"),
        "source_url": post.get("source_url"),
        "posted_at": post.get("posted_at"),
        "captured_at": post.get("captured_at"),
    }
    freshness_context = {
        "posted_at": post.get("posted_at"),
        "captured_at": post.get("captured_at"),
        "source_freshness": "source_post_timestamp",
        "profile_window": "unknown",
        "update_language": _has_update_language(str(post.get("text") or "")),
        "negative_status_language": _has_negative_language(str(post.get("text") or "")),
    }
    return {
        "schema": "aoa_connector_claim_v1",
        "claim_id": claim_id,
        "claim_kind": claim_kind,
        "method_id": method_id,
        "method_kind": method_kind,
        "method_label": label if claim_kind == "method" else None,
        "action": action_label,
        "label": label,
        "target_labels": _unique(target_labels),
        "tool_labels": _unique(tool_labels),
        "condition_labels": _unique(condition_labels),
        "applicability_context": _unique(context_labels),
        "risk_labels": _unique(risk_labels),
        "warning_labels": _unique(warning_labels),
        "source_post": source_post,
        "source_post_id": post.get("post_id"),
        "source_url": post.get("source_url"),
        "posted_at": post.get("posted_at"),
        "captured_at": post.get("captured_at"),
        "evidence_span": evidence_span,
        "freshness_context": freshness_context,
        "confidence": confidence,
        "confidence_basis": {"basis": extraction_rule, "extractor_version": CLAIM_EXTRACTOR_VERSION},
        "manual_review_required": manual_review_required,
    }


def _append_cross_claim_edges(edges: list[dict[str, object]], claims: list[dict[str, object]]) -> None:
    for claim in claims:
        for other in claims:
            if claim is other or claim.get("claim_id") == other.get("claim_id"):
                continue
            if not _related_claims(claim, other):
                continue
            newer = _claim_time_sort_key(claim) > _claim_time_sort_key(other)
            if claim.get("claim_kind") == "warning" and other.get("claim_kind") != "warning":
                _append_claim_edge(edges, "claim_contextualizes_claim", str(claim["claim_id"]), str(other["claim_id"]), claim, confidence=0.55)
                if set(_strings(claim.get("risk_labels", []))).intersection({"bootloop", "brick", "data_loss", "data_wipe"}):
                    _append_claim_edge(edges, "claim_contradicts_claim", str(claim["claim_id"]), str(other["claim_id"]), claim, confidence=0.52)
            if newer and _has_freshness_update(claim):
                _append_claim_edge(edges, "claim_supersedes_claim", str(claim["claim_id"]), str(other["claim_id"]), claim, confidence=0.58)
            if newer and _has_negative_status(claim) and other.get("claim_kind") == "method":
                _append_claim_edge(edges, "claim_deprecated_for_context", str(other["claim_id"]), str(claim["claim_id"]), claim, confidence=0.58)
                _append_claim_edge(edges, "claim_contradicts_claim", str(claim["claim_id"]), str(other["claim_id"]), claim, confidence=0.6)


def _append_claim_edge(
    edges: list[dict[str, object]],
    kind: str,
    from_node: str,
    to_node: str,
    claim: dict[str, object],
    *,
    confidence: float,
) -> None:
    edge_id = f"{from_node}->{to_node}:{kind}:{claim.get('source_post_id')}"
    if any(edge.get("edge_id") == edge_id for edge in edges):
        return
    edges.append(
        {
            "schema": "aoa_connector_claim_relation_v1",
            "edge_id": edge_id,
            "kind": kind,
            "from_node": from_node,
            "to_node": to_node,
            "source_refs": [str(claim.get("source_url") or "")],
            "source_post_ids": [str(claim.get("source_post_id") or "")],
            "confidence": confidence,
            "extraction_basis": RELATION_EXTRACTOR_VERSION,
            "relation_reason": _default_relation_reason(kind),
            "freshness_basis": "posted_at_then_post_order",
            "manual_review_required": bool(claim.get("manual_review_required")),
            "posted_at": claim.get("posted_at"),
            "captured_at": claim.get("captured_at"),
        }
    )


def _default_relation_reason(kind: str) -> str:
    if kind == "claim_supersedes_claim":
        return "newer related claim carries current/update language"
    if kind == "claim_contradicts_claim":
        return "risk or negative status language conflicts with method claim"
    if kind == "claim_deprecated_for_context":
        return "newer negative status language demotes older method for context"
    if kind.startswith("source_"):
        return "source post directly supports relation"
    return "deterministic claim/entity extraction"


def _related_claims(left: dict[str, object], right: dict[str, object]) -> bool:
    left_targets = set(_strings(left.get("target_labels", [])))
    right_targets = set(_strings(right.get("target_labels", [])))
    left_context = set(_strings(left.get("applicability_context", [])))
    right_context = set(_strings(right.get("applicability_context", [])))
    if left_targets and right_targets and left_targets.intersection(right_targets):
        return True
    return bool(left_context and right_context and left_context.intersection(right_context))


def _has_freshness_update(claim: dict[str, object]) -> bool:
    freshness = claim.get("freshness_context", {})
    if isinstance(freshness, dict) and freshness.get("update_language"):
        return True
    text = str(claim.get("action") or "").casefold()
    return any(term in text for term in ["current", "supersedes", "after", "stale"])


def _has_negative_status(claim: dict[str, object]) -> bool:
    freshness = claim.get("freshness_context", {})
    if isinstance(freshness, dict) and freshness.get("negative_status_language"):
        return True
    return "no longer" in str(claim.get("action") or "").casefold()


def _entities_by_kind(entities: list[dict[str, object]], kind: str) -> list[dict[str, object]]:
    return [entity for entity in entities if entity.get("kind") == kind]


def _labels_by_kind(entities: list[dict[str, object]], kind: str) -> list[str]:
    return _unique([str(entity.get("value")) for entity in entities if entity.get("kind") == kind and entity.get("value")])


def _tool_labels(entities: list[dict[str, object]], allowed: set[str] | None = None) -> list[str]:
    labels = _labels_by_kind(entities, "tool")
    if allowed is not None:
        labels = [label for label in labels if label in allowed]
    return labels


def _context_labels(entities: list[dict[str, object]]) -> list[str]:
    labels: list[str] = []
    for kind in ["device", "codename", "android_version", "build_id", "firmware_family"]:
        labels.extend(_labels_by_kind(entities, kind))
    return _unique(labels)


def _targets_for_action(action_label: str, entities: list[dict[str, object]]) -> list[str]:
    action = action_label.casefold()
    targets = [
        str(entity.get("value"))
        for entity in entities
        if entity.get("kind") == "file" and str(entity.get("value") or "").casefold() in action
    ]
    return _unique(targets or _labels_by_kind(entities, "file"))


def _warning_target_labels(warning_label: str, entities: list[dict[str, object]]) -> list[str]:
    lowered = warning_label.casefold()
    labels = [
        str(entity.get("value"))
        for entity in entities
        if entity.get("kind") in {"file", "device", "codename", "android_version", "build_id"}
        and str(entity.get("value") or "").casefold() in lowered
    ]
    return _unique(labels or _labels_by_kind(entities, "file"))


def _claim_label(action_label: str, target_labels: list[str], tool_labels: list[str], context_labels: list[str]) -> str:
    pieces = [action_label]
    if target_labels:
        pieces.append("target=" + ",".join(target_labels[:3]))
    if tool_labels:
        pieces.append("tool=" + ",".join(tool_labels[:3]))
    if context_labels:
        pieces.append("context=" + ",".join(context_labels[:4]))
    return " | ".join(piece for piece in pieces if piece)


def _evidence_span(text: str, needle: str) -> dict[str, object]:
    lowered = text.casefold()
    needle_lower = needle.casefold()
    start = lowered.find(needle_lower)
    if start < 0:
        start = 0
    end = min(len(text), start + max(len(needle), 180))
    return {"type": "excerpt", "char_start": start, "char_end": end, "text": text[start:end]}


def _has_update_language(text: str) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in ["after", "current", "no longer", "stale", "supersedes", "newer", "latest"])


def _has_negative_language(text: str) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in ["no longer", "stale", "do not", "caused bootloop", "data loss"])


def _dedupe_claims(claims: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    deduped: list[dict[str, object]] = []
    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        if claim_id in seen:
            continue
        seen.add(claim_id)
        deduped.append(claim)
    return deduped


def _relation_key(claim: dict[str, object]) -> str:
    return "|".join(
        [
            str(claim.get("method_kind") or claim.get("claim_kind") or ""),
            ",".join(sorted(_strings(claim.get("target_labels", [])))),
            ",".join(sorted(_strings(claim.get("tool_labels", [])))),
        ]
    )


def _claim_time_sort_key(claim: dict[str, object]) -> tuple[int, str, int]:
    parsed = _parse_time(claim.get("posted_at"))
    post_order = _post_order(claim.get("source_post_id"))
    if parsed:
        return (1, parsed.isoformat(), post_order)
    return (0, str(claim.get("claim_id") or ""), post_order)


def _post_order(value: object) -> int:
    digits = re.sub(r"\D+", "", str(value or ""))
    return int(digits) if digits else 0


def _parse_time(value: object) -> datetime | None:
    text = str(value or "")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _upsert_node(nodes: dict[str, dict[str, object]], node_id: str, kind: str, label: str, source_url: str, confidence: float) -> None:
    node = nodes.setdefault(
        node_id,
        {
            "schema": "aoa_xda_graph_node_v1",
            "node_id": node_id,
            "kind": kind,
            "label": label,
            "source_refs": [],
            "confidence": confidence,
        },
    )
    if source_url and source_url not in node["source_refs"]:
        node["source_refs"].append(source_url)


def _action_node_id(label: object) -> str:
    text = str(label or "")
    return f"action:{_slug(text)}" if text else ""


def _target_node_id(label: str) -> str:
    return f"target:{_slug(label)}"


def _tool_node_id(label: str) -> str:
    return f"tool:{_slug(label)}"


def _condition_node_id(label: str) -> str:
    return f"condition:{_slug(label)}"


def _context_node_id(label: str) -> str:
    return f"context:{_slug(label)}"


def _warning_node_id(label: str) -> str:
    return f"warning:{_slug(label)}"


def _slug(value: object) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "-", str(value).casefold()).strip("-")[:80] or "item"


def _strings(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(item) for item in items if str(item)]


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
