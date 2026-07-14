from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from aoa_xda_connector.graph import build_graph
from aoa_xda_connector.normalize import normalize_snapshot


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    REPO_ROOT
    / "connector"
    / "fixtures"
    / "html"
    / "xda_pixel_8_pro_husky_root_thread.html"
)
FIXTURE_URL = (
    "https://xdaforums.com/t/pixel-8-pro-husky-root-recovery-proof.4633839/"
)
PORT_PATH = REPO_ROOT / "stats" / "port.manifest.json"
PACKET_PATH = (
    REPO_ROOT
    / "stats"
    / "packets"
    / "starter-actionable-entity-claim-traceability-ratio.reference.json"
)
ACTIONABLE_KINDS = {
    "root_action",
    "recovery_action",
    "warning",
    "status",
}
EXPECTED_SOURCE_RELATION = {
    "root_action": "source_supports_claim",
    "recovery_action": "source_supports_claim",
    "warning": "source_warns_about_claim",
    "status": "source_supports_claim",
}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalized_and_graph(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    normalized_path = normalize_snapshot(
        FIXTURE_PATH,
        FIXTURE_URL,
        tmp_path / "normalized",
    )
    graph_path = build_graph(normalized_path.parent, tmp_path / "graph")
    return load_json(normalized_path), load_json(graph_path)


def _unknown(reason: str) -> dict[str, object]:
    return {"status": "unknown", "reason": reason}


def _actionable_population(
    normalized: object,
) -> dict[tuple[str, str, str], str]:
    if (
        not isinstance(normalized, dict)
        or normalized.get("schema") != "aoa_xda_normalized_topic_v1"
    ):
        raise ValueError("malformed_or_unsupported_normalized_topic")
    posts = normalized.get("posts")
    if (
        not isinstance(posts, list)
        or not posts
        or any(not isinstance(post, dict) for post in posts)
    ):
        raise ValueError("malformed_normalized_post_collection")

    population: dict[tuple[str, str, str], str] = {}
    post_ids: set[str] = set()
    for post in posts:
        post_id = post.get("post_id")
        source_url = post.get("source_url")
        entities = post.get("entities")
        if (
            not isinstance(post_id, str)
            or not post_id
            or post_id in post_ids
            or not isinstance(source_url, str)
            or not source_url
            or not isinstance(entities, list)
            or any(not isinstance(entity, dict) for entity in entities)
        ):
            raise ValueError("malformed_or_duplicate_normalized_post")
        post_ids.add(post_id)
        for entity in entities:
            kind = entity.get("kind")
            if kind not in ACTIONABLE_KINDS:
                continue
            value = entity.get("value")
            if not isinstance(value, str) or not value:
                raise ValueError("malformed_actionable_entity")
            key = (post_id, str(kind), value)
            if key in population:
                raise ValueError("duplicate_actionable_entity")
            population[key] = source_url

    if not population:
        raise ValueError("empty_actionable_population")
    return population


def _mapped_actionable_kind(claim: dict[str, object]) -> str | None:
    claim_kind = claim.get("claim_kind")
    method_kind = claim.get("method_kind")
    if claim_kind == "method":
        if method_kind == "root":
            return "root_action"
        if method_kind == "recovery":
            return "recovery_action"
        return None
    if claim_kind == "warning":
        if method_kind != "risk_warning":
            raise ValueError("contradictory_warning_method_kind")
        return "warning"
    if claim_kind == "status":
        if method_kind != "freshness_update":
            raise ValueError("contradictory_status_method_kind")
        return "status"
    return None


def derive_actionable_claim_traceability_ratio(
    normalized: object,
    graph: object,
) -> dict[str, object]:
    try:
        population = _actionable_population(normalized)
    except ValueError as exc:
        return _unknown(str(exc))

    if (
        not isinstance(graph, dict)
        or graph.get("schema") != "aoa_xda_graph_export_v1"
        or not isinstance(graph.get("nodes"), list)
        or not isinstance(graph.get("edges"), list)
        or any(not isinstance(node, dict) for node in graph["nodes"])
        or any(not isinstance(edge, dict) for edge in graph["edges"])
    ):
        return _unknown("malformed_or_unsupported_graph")

    claims: dict[tuple[str, str, str], tuple[str, str]] = {}
    claim_ids: set[str] = set()
    try:
        for node in graph["nodes"]:
            if node.get("kind") != "claim":
                continue
            claim = node.get("claim")
            if (
                node.get("schema") != "aoa_connector_claim_node_v1"
                or not isinstance(claim, dict)
                or claim.get("schema") != "aoa_connector_claim_v1"
            ):
                raise ValueError("malformed_claim_node")
            claim_id = claim.get("claim_id")
            if (
                not isinstance(claim_id, str)
                or not claim_id
                or node.get("node_id") != claim_id
                or claim_id in claim_ids
            ):
                raise ValueError("malformed_or_duplicate_claim_identity")
            claim_ids.add(claim_id)

            actionable_kind = _mapped_actionable_kind(claim)
            if actionable_kind is None:
                continue
            post_id = claim.get("source_post_id")
            action = claim.get("action")
            source_url = claim.get("source_url")
            source_refs = node.get("source_refs")
            if (
                not isinstance(post_id, str)
                or not post_id
                or not isinstance(action, str)
                or not action
                or not isinstance(source_url, str)
                or not source_url
                or not isinstance(source_refs, list)
                or any(not isinstance(ref, str) for ref in source_refs)
                or source_url not in source_refs
            ):
                raise ValueError("malformed_claim_source_identity")
            key = (post_id, actionable_kind, action)
            if key not in population:
                raise ValueError("unexpected_relevant_claim")
            if population[key] != source_url:
                raise ValueError("contradictory_claim_source_identity")
            if key in claims:
                raise ValueError("duplicate_relevant_claim")
            claims[key] = (claim_id, source_url)
    except ValueError as exc:
        return _unknown(str(exc))

    traceable: set[tuple[str, str, str]] = set()
    try:
        for key, (claim_id, source_url) in claims.items():
            post_id, actionable_kind, _ = key
            expected_kind = EXPECTED_SOURCE_RELATION[actionable_kind]
            matching_edges = []
            for edge in graph["edges"]:
                if edge.get("kind") != expected_kind or edge.get("to_node") != claim_id:
                    continue
                if (
                    edge.get("schema") != "aoa_connector_claim_relation_v1"
                    or edge.get("from_node") != f"post:{post_id}"
                    or not isinstance(edge.get("source_refs"), list)
                    or source_url not in edge["source_refs"]
                    or not isinstance(edge.get("source_post_ids"), list)
                    or post_id not in edge["source_post_ids"]
                ):
                    raise ValueError("contradictory_source_trace")
                matching_edges.append(edge)
            if len(matching_edges) > 1:
                raise ValueError("duplicate_source_trace")
            if matching_edges:
                traceable.add(key)
    except ValueError as exc:
        return _unknown(str(exc))

    declared_by_kind = Counter(key[1] for key in population)
    traceable_by_kind = Counter(key[1] for key in traceable)
    denominator = len(population)
    numerator = len(traceable)
    return {
        "status": "observed",
        "numerator": numerator,
        "denominator": denominator,
        "ratio": numerator / denominator,
        "breakdown": {
            kind: {
                "traceable": traceable_by_kind[kind],
                "declared": declared_by_kind[kind],
            }
            for kind in sorted(declared_by_kind)
        },
        "gap_count": denominator - numerator,
    }


def test_reference_packet_matches_current_starter_traceability_census(
    tmp_path: Path,
) -> None:
    normalized, graph = normalized_and_graph(tmp_path)
    derived = derive_actionable_claim_traceability_ratio(normalized, graph)
    packet = load_json(PACKET_PATH)

    assert derived == {
        "status": "observed",
        "numerator": 10,
        "denominator": 10,
        "ratio": 1.0,
        "breakdown": {
            "recovery_action": {"traceable": 3, "declared": 3},
            "root_action": {"traceable": 3, "declared": 3},
            "status": {"traceable": 2, "declared": 2},
            "warning": {"traceable": 2, "declared": 2},
        },
        "gap_count": 0,
    }
    assert packet["population"]["size"] == 10
    assert packet["sample"]["size"] == 10
    assert packet["value"] == {
        "status": "observed",
        "kind": "ratio",
        "unit": "1",
        "number": 1.0,
        "numerator": 10,
        "denominator": 10,
    }
    assert packet["progress"] == {"state": "terminal", "completed": 10, "total": 10}


def test_missing_claim_and_source_trace_are_observed_gaps(tmp_path: Path) -> None:
    normalized, graph = normalized_and_graph(tmp_path)
    claim_node = next(node for node in graph["nodes"] if node.get("kind") == "claim")
    claim_id = claim_node["node_id"]

    missing_claim = deepcopy(graph)
    missing_claim["nodes"] = [
        node for node in missing_claim["nodes"] if node.get("node_id") != claim_id
    ]
    missing_claim["edges"] = [
        edge
        for edge in missing_claim["edges"]
        if edge.get("from_node") != claim_id and edge.get("to_node") != claim_id
    ]

    missing_trace = deepcopy(graph)
    missing_trace["edges"] = [
        edge
        for edge in missing_trace["edges"]
        if not (
            edge.get("to_node") == claim_id
            and edge.get("kind") == "source_supports_claim"
        )
    ]

    for case in (missing_claim, missing_trace):
        derived = derive_actionable_claim_traceability_ratio(normalized, case)
        assert derived["status"] == "observed"
        assert derived["numerator"] == 9
        assert derived["denominator"] == 10
        assert derived["ratio"] == 0.9
        assert derived["gap_count"] == 1


def test_valid_graph_without_relevant_claims_is_observed_zero(tmp_path: Path) -> None:
    normalized, graph = normalized_and_graph(tmp_path)
    claim_ids = {
        node["node_id"] for node in graph["nodes"] if node.get("kind") == "claim"
    }
    graph["nodes"] = [node for node in graph["nodes"] if node.get("kind") != "claim"]
    graph["edges"] = [
        edge
        for edge in graph["edges"]
        if edge.get("from_node") not in claim_ids
        and edge.get("to_node") not in claim_ids
    ]

    derived = derive_actionable_claim_traceability_ratio(normalized, graph)

    assert derived["status"] == "observed"
    assert derived["numerator"] == 0
    assert derived["denominator"] == 10
    assert derived["ratio"] == 0.0
    assert derived["gap_count"] == 10


def test_malformed_duplicate_unexpected_and_contradictory_inputs_are_unknown(
    tmp_path: Path,
) -> None:
    normalized, graph = normalized_and_graph(tmp_path)

    empty_population = deepcopy(normalized)
    for post in empty_population["posts"]:
        post["entities"] = [
            entity
            for entity in post["entities"]
            if entity.get("kind") not in ACTIONABLE_KINDS
        ]
    duplicate_population = deepcopy(normalized)
    actionable = next(
        entity
        for entity in duplicate_population["posts"][0]["entities"]
        if entity.get("kind") in ACTIONABLE_KINDS
    )
    duplicate_population["posts"][0]["entities"].append(deepcopy(actionable))

    duplicate_claim = deepcopy(graph)
    duplicate_claim["nodes"].append(
        deepcopy(next(node for node in duplicate_claim["nodes"] if node.get("kind") == "claim"))
    )
    unexpected_claim = deepcopy(graph)
    unexpected_node = next(
        node for node in unexpected_claim["nodes"] if node.get("kind") == "claim"
    )
    unexpected_node["claim"]["action"] = "unexpected actionable value"

    contradictory_source = deepcopy(graph)
    contradictory_node = next(
        node for node in contradictory_source["nodes"] if node.get("kind") == "claim"
    )
    contradictory_node["claim"]["source_url"] = "https://example.invalid/other-source"
    contradictory_node["source_refs"] = ["https://example.invalid/other-source"]

    unsupported_normalized = deepcopy(normalized)
    unsupported_normalized["schema"] = "aoa_xda_normalized_topic_v2"
    unsupported_graph = deepcopy(graph)
    unsupported_graph["schema"] = "aoa_xda_graph_export_v2"

    cases = (
        derive_actionable_claim_traceability_ratio(None, graph),
        derive_actionable_claim_traceability_ratio(empty_population, graph),
        derive_actionable_claim_traceability_ratio(duplicate_population, graph),
        derive_actionable_claim_traceability_ratio(normalized, {"schema": "wrong"}),
        derive_actionable_claim_traceability_ratio(normalized, duplicate_claim),
        derive_actionable_claim_traceability_ratio(normalized, unexpected_claim),
        derive_actionable_claim_traceability_ratio(normalized, contradictory_source),
        derive_actionable_claim_traceability_ratio(unsupported_normalized, graph),
        derive_actionable_claim_traceability_ratio(normalized, unsupported_graph),
    )

    assert all(case["status"] == "unknown" for case in cases)


def test_measurement_stays_reference_only_and_below_source_eval_and_runtime_authority() -> None:
    port = load_json(PORT_PATH)
    measurement = port["measurements"][0]
    packet = load_json(PACKET_PATH)
    serialized_packet = PACKET_PATH.read_text(encoding="utf-8")

    assert port["evidence_posture"] == {
        "live_state": "reference_only",
        "privacy": "public",
        "raw_content_allowed": False,
    }
    assert measurement["live_state"] == {"capability": "reference_only"}
    assert measurement["aggregation"] == {
        "operator": "ratio_of_sums",
        "across": ["dimension"],
    }
    assert measurement["dimensions"]["allowed"] == [
        {
            "name": "actionable_entity_kind",
            "max_cardinality": 4,
            "sensitivity": "public",
        }
    ]
    assert "claim truth" in measurement["authority_ceiling"]
    assert "answer quality" in measurement["authority_ceiling"]
    assert "eval success" in measurement["authority_ceiling"]
    assert packet["posture"]["raw_content_included"] is False
    assert packet["dimensions"] == {}
    assert packet["provenance"]["source_revision"] == (
        "0bce839df06edba50553fb34ca758716792b05f6"
    )
    for forbidden in (
        '"post_id"',
        '"claim_id"',
        '"source_url"',
        "#post-",
        "claim:",
        "/srv/",
        ".aoa",
    ):
        assert forbidden not in serialized_packet
