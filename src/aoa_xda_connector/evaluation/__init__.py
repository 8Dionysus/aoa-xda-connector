"""Local eval suite runners for the XDA connector."""

from __future__ import annotations

import json
from pathlib import Path

from aoa_xda_connector.answer import render_answer_packet
from aoa_xda_connector.config import StorageRoots, find_repo_root
from aoa_xda_connector.graph import build_graph
from aoa_xda_connector.index import build_keyword_index
from aoa_xda_connector.normalize import normalize_snapshot
from aoa_xda_connector.query import query_graph_packet


SOURCE_URL = "https://xdaforums.com/t/pixel-8-pro-husky-root-recovery-proof.4633839/"


def ensure_fixture_run(run_id: str = "starter-fixture", profile_id: str = "pixel-8-pro-husky") -> dict[str, Path]:
    repo_root = find_repo_root()
    roots = StorageRoots.from_env(repo_root)
    if not roots.data or not roots.artifact:
        raise RuntimeError("Storage roots are incomplete")
    fixture = repo_root / "connector" / "fixtures" / "html" / "xda_pixel_8_pro_husky_root_thread.html"
    normalized_dir = roots.data / "runs" / run_id / "normalized"
    index_dir = roots.artifact / "indexes" / run_id
    graph_dir = roots.artifact / "graphs" / run_id
    normalize_snapshot(fixture, SOURCE_URL, normalized_dir)
    index_path = build_keyword_index(normalized_dir, index_dir, profile_id=profile_id)
    graph_path = build_graph(normalized_dir, graph_dir, profile_id=profile_id)
    return {"normalized_dir": normalized_dir, "index_path": index_path, "graph_path": graph_path}


def run_claim_relation_suite(suite_path: Path, repo_root: Path | None = None) -> dict[str, object]:
    repo_root = repo_root or find_repo_root()
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    paths = ensure_fixture_run()
    graph = json.loads(paths["graph_path"].read_text(encoding="utf-8"))
    node_kinds = {str(node.get("kind")) for node in graph.get("nodes", []) if isinstance(node, dict)}
    relation_kinds = {str(edge.get("kind")) for edge in graph.get("edges", []) if isinstance(edge, dict)}
    claims = [
        node.get("claim")
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("kind") == "claim" and isinstance(node.get("claim"), dict)
    ]
    failures: list[str] = []
    for case in suite.get("cases", []):
        expect = case.get("expect", {})
        if graph.get("claim_stats", {}).get("claim_count", 0) < expect.get("min_claim_count", 0):
            failures.append(f"{case.get('case_id')}: too few claims")
        if graph.get("claim_stats", {}).get("warning_count", 0) < expect.get("min_warning_claim_count", 0):
            failures.append(f"{case.get('case_id')}: too few warning claims")
        for kind in expect.get("node_kinds", []):
            if kind not in node_kinds:
                failures.append(f"{case.get('case_id')}: missing node kind {kind}")
        for kind in expect.get("relation_kinds", []):
            if kind not in relation_kinds:
                failures.append(f"{case.get('case_id')}: missing relation kind {kind}")
        claim_text = json.dumps(claims, ensure_ascii=False)
        for token in expect.get("claim_text_contains", []):
            if token.casefold() not in claim_text.casefold():
                failures.append(f"{case.get('case_id')}: missing claim token {token}")
    return {
        "schema": "aoa_xda_claim_graph_eval_report_v1",
        "suite_id": suite.get("suite_id"),
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "network_touched": False,
        "read_only": True,
        "graph_path": str(paths["graph_path"]),
        "claim_stats": graph.get("claim_stats", {}),
    }


def run_answer_packet_suite(suite_path: Path, repo_root: Path | None = None) -> dict[str, object]:
    repo_root = repo_root or find_repo_root()
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    paths = ensure_fixture_run()
    failures: list[str] = []
    case_reports: list[dict[str, object]] = []
    for case in suite.get("cases", []):
        packet = query_graph_packet(paths["index_path"], paths["graph_path"], str(case.get("query") or ""), limit=5)
        answer = render_answer_packet(packet, limit=5)
        expect = case.get("expect", {})
        failures.extend(_check_answer_expectations(str(case.get("case_id")), answer, expect))
        case_reports.append(
            {
                "case_id": case.get("case_id"),
                "answer_status": answer.get("answer_report", {}).get("answer_status"),
                "conflict_status": answer.get("conflict_report", {}).get("status"),
                "freshness_status": answer.get("freshness_report", {}).get("status"),
                "warning_status": answer.get("warning_report", {}).get("status"),
            }
        )
    return {
        "schema": "aoa_xda_answer_eval_report_v1",
        "suite_id": suite.get("suite_id"),
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "cases": case_reports,
        "network_touched": False,
        "read_only": True,
    }


def _check_answer_expectations(case_id: str, answer: dict[str, object], expect: dict[str, object]) -> list[str]:
    failures: list[str] = []
    answer_report = answer.get("answer_report", {})
    conflict = answer.get("conflict_report", {})
    freshness = answer.get("freshness_report", {})
    warning = answer.get("warning_report", {})
    applicability = answer.get("applicability_report", {})
    if answer_report.get("answer_status") != expect.get("answer_status"):
        failures.append(f"{case_id}: answer_status")
    if "conflict_status" in expect and conflict.get("status") != expect["conflict_status"]:
        failures.append(f"{case_id}: conflict_status")
    if "conflict_status_any" in expect and conflict.get("status") not in expect["conflict_status_any"]:
        failures.append(f"{case_id}: conflict_status_any")
    if "freshness_status" in expect and freshness.get("status") != expect["freshness_status"]:
        failures.append(f"{case_id}: freshness_status")
    if "freshness_status_any" in expect and freshness.get("status") not in expect["freshness_status_any"]:
        failures.append(f"{case_id}: freshness_status_any")
    if "warning_status" in expect and warning.get("status") != expect["warning_status"]:
        failures.append(f"{case_id}: warning_status")
    if "applicability_status" in expect and applicability.get("status") != expect["applicability_status"]:
        failures.append(f"{case_id}: applicability_status")
    if expect.get("network_touched") is not None and answer.get("network_touched") is not expect["network_touched"]:
        failures.append(f"{case_id}: network_touched")
    if expect.get("read_only") is not None and answer.get("read_only") is not expect["read_only"]:
        failures.append(f"{case_id}: read_only")
    if expect.get("requires_claim_ids") and not any(step.get("claim_ids") for step in answer.get("evidence_chain", [])):
        failures.append(f"{case_id}: missing claim ids")
    if expect.get("requires_post_ids") and not any(step.get("post_id") for step in answer.get("evidence_chain", [])):
        failures.append(f"{case_id}: missing post ids")
    if expect.get("requires_source_urls") and not any(step.get("source_url") for step in answer.get("evidence_chain", [])):
        failures.append(f"{case_id}: missing source urls")
    if int(expect.get("min_superseding_claims", 0)) > len(conflict.get("superseding_claim_ids", [])):
        failures.append(f"{case_id}: too few superseding claims")
    text = json.dumps(answer, ensure_ascii=False)
    for token in expect.get("answer_text_contains", []):
        if token.casefold() not in text.casefold():
            failures.append(f"{case_id}: missing answer text {token}")
    for token in expect.get("context_contains", []):
        if token not in applicability.get("contexts", []):
            failures.append(f"{case_id}: missing context {token}")
    for token in expect.get("condition_contains", []):
        if token not in applicability.get("conditions", []):
            failures.append(f"{case_id}: missing condition {token}")
    return failures
