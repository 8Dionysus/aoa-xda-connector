"""Command line interface for the XDA connector."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from aoa_xda_connector.answer import render_answer_packet
from aoa_xda_connector.config import StorageRoots, find_repo_root
from aoa_xda_connector.evaluation import SOURCE_URL, run_answer_packet_suite, run_claim_relation_suite
from aoa_xda_connector.graph import build_graph
from aoa_xda_connector.index import build_keyword_index
from aoa_xda_connector.normalize import normalize_snapshot
from aoa_xda_connector.policy.rules import route_decision
from aoa_xda_connector.query import query_graph_packet, query_keyword_index
from aoa_xda_connector.storage import create_storage_roots, storage_status


DEFAULT_PROFILE = "pixel-8-pro-husky"
DEFAULT_RUN = "starter-fixture"
DEFAULT_CLAIM_RELATIONS_SUITE = Path("evals/suites/starter_claim_conflict_relations.json")
DEFAULT_ANSWER_SUITE = Path("evals/suites/starter_claim_answer_packets.json")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aoa-xda")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Check local skeleton and storage posture.")
    doctor.set_defaults(func=cmd_doctor)

    init = sub.add_parser("init", help="Prepare configured storage roots.")
    init.set_defaults(func=cmd_init)

    storage = sub.add_parser("storage", help="Inspect configured storage roots.")
    storage_sub = storage.add_subparsers(dest="storage_command", required=True)
    storage_status_parser = storage_sub.add_parser("status")
    storage_status_parser.add_argument("--measure", action="store_true")
    storage_status_parser.set_defaults(func=cmd_storage_status)

    policy = sub.add_parser("policy", help="Policy commands.")
    policy_sub = policy.add_subparsers(dest="policy_command", required=True)
    policy_check = policy_sub.add_parser("check")
    policy_check.set_defaults(func=cmd_policy_check)

    materialize = sub.add_parser("materialize", help="Materialize no-network starter datasets.")
    materialize_sub = materialize.add_subparsers(dest="materialize_command", required=True)
    fixture = materialize_sub.add_parser("fixture")
    fixture.add_argument("--run", default=DEFAULT_RUN)
    fixture.add_argument("--profile", default=DEFAULT_PROFILE)
    fixture.set_defaults(func=cmd_materialize_fixture)

    build_index = sub.add_parser("build-index", help="Build local keyword index.")
    build_index.add_argument("--run", default=DEFAULT_RUN)
    build_index.add_argument("--profile", default=DEFAULT_PROFILE)
    build_index.set_defaults(func=cmd_build_index)

    build_graph_parser = sub.add_parser("build-graph", help="Build local graph export.")
    build_graph_parser.add_argument("--run", default=DEFAULT_RUN)
    build_graph_parser.add_argument("--profile", default=DEFAULT_PROFILE)
    build_graph_parser.set_defaults(func=cmd_build_graph)

    query = sub.add_parser("query", help="Query local keyword index.")
    query.add_argument("query")
    query.add_argument("--run", default=DEFAULT_RUN)
    query.add_argument("--limit", type=int, default=5)
    query.set_defaults(func=cmd_query)

    query_graph = sub.add_parser("query-graph", help="Query local keyword index with graph context.")
    query_graph.add_argument("query")
    query_graph.add_argument("--run", default=DEFAULT_RUN)
    query_graph.add_argument("--limit", type=int, default=5)
    query_graph.set_defaults(func=cmd_query_graph)

    answer = sub.add_parser("answer", help="Render an answer packet from local graph evidence.")
    answer.add_argument("query")
    answer.add_argument("--run", default=DEFAULT_RUN)
    answer.add_argument("--limit", type=int, default=5)
    answer.set_defaults(func=cmd_answer)

    eval_parser = sub.add_parser("eval", help="Run local connector eval suites.")
    eval_sub = eval_parser.add_subparsers(dest="eval_command", required=True)
    claim_relations = eval_sub.add_parser("claim-relations")
    claim_relations.add_argument("--suite", default=str(DEFAULT_CLAIM_RELATIONS_SUITE))
    claim_relations.set_defaults(func=cmd_eval_claim_relations)
    answer_packets = eval_sub.add_parser("answer-packets")
    answer_packets.add_argument("--suite", default=str(DEFAULT_ANSWER_SUITE))
    answer_packets.set_defaults(func=cmd_eval_answer_packets)

    return parser


def cmd_doctor(_args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    roots = StorageRoots.from_env(repo_root)
    required = [
        "AGENTS.md",
        "README.md",
        "BOUNDARIES.md",
        "connector/SOURCE_POLICY.md",
        "connector/STORAGE_POLICY.md",
        "docs/RUNTIME_CONTRACT.md",
        "connector/fixtures/html/xda_pixel_8_pro_husky_root_thread.html",
    ]
    missing = [rel for rel in required if not (repo_root / rel).exists()]
    payload = {
        "schema": "aoa_xda_doctor_v1",
        "status": "ok" if not missing else "error",
        "repo_root": str(repo_root),
        "missing": missing,
        "storage": storage_status(repo_root, roots),
        "network_touched": False,
        "read_only": True,
    }
    _emit(payload)
    return 0 if not missing else 1


def cmd_init(_args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    created = create_storage_roots(roots)
    _emit({"schema": "aoa_xda_init_v1", "status": "ok", "created": created, "network_touched": False})
    return 0


def cmd_storage_status(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    roots = StorageRoots.from_env(repo_root)
    _emit(storage_status(repo_root, roots, measure=args.measure))
    return 0


def cmd_policy_check(_args: argparse.Namespace) -> int:
    samples = [
        SOURCE_URL,
        "https://xdaforums.com/search/123/",
        "https://xdaforums.com/account/",
        "https://xdaforums.com/attachments/file.zip",
        "https://xdaforums.com/t/safe-thread.1/",
    ]
    decisions = [route_decision(url) for url in samples]
    ok = decisions[0]["allowed"] is True and all(item["allowed"] is False for item in decisions[1:4])
    _emit({"schema": "aoa_xda_policy_check_v1", "status": "ok" if ok else "error", "decisions": decisions, "network_touched": False})
    return 0 if ok else 1


def cmd_materialize_fixture(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    roots = StorageRoots.from_env(repo_root)
    if not roots.data or not roots.artifact:
        return _missing_roots(roots)
    create_storage_roots(roots)
    fixture = repo_root / "connector" / "fixtures" / "html" / "xda_pixel_8_pro_husky_root_thread.html"
    run_root = roots.data / "runs" / args.run
    raw_dir = run_root / "raw"
    normalized_dir = run_root / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / fixture.name
    shutil.copyfile(fixture, raw_path)
    normalized_path = normalize_snapshot(raw_path, SOURCE_URL, normalized_dir)
    receipt = {
        "schema": "aoa_xda_materialize_receipt_v1",
        "run_id": args.run,
        "profile_id": args.profile,
        "source_url": SOURCE_URL,
        "fixture": str(fixture.relative_to(repo_root)),
        "raw_path": str(raw_path),
        "normalized_path": str(normalized_path),
        "created_at": _now(),
        "network_touched": False,
        "read_only": True,
    }
    receipt_path = _write_receipt(roots.artifact / "receipts", args.run, "materialize", receipt)
    _emit({"status": "ok", "receipt": str(receipt_path), **receipt})
    return 0


def cmd_build_index(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    roots = StorageRoots.from_env(repo_root)
    if not roots.data or not roots.artifact:
        return _missing_roots(roots)
    normalized_dir = roots.data / "runs" / args.run / "normalized"
    index_path = build_keyword_index(normalized_dir, roots.artifact / "indexes" / args.run, profile_id=args.profile)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    receipt = {
        "schema": "aoa_xda_index_manifest_v1",
        "run_id": args.run,
        "profile_id": args.profile,
        "index_path": str(index_path),
        "doc_count": index.get("doc_count"),
        "term_count": index.get("term_count"),
        "created_at": _now(),
        "network_touched": False,
        "read_only": True,
    }
    receipt_path = _write_receipt(roots.artifact / "receipts", args.run, "index", receipt)
    _emit({"status": "ok", "receipt": str(receipt_path), **receipt})
    return 0


def cmd_build_graph(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    roots = StorageRoots.from_env(repo_root)
    if not roots.data or not roots.artifact:
        return _missing_roots(roots)
    normalized_dir = roots.data / "runs" / args.run / "normalized"
    graph_path = build_graph(normalized_dir, roots.artifact / "graphs" / args.run, profile_id=args.profile)
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    receipt = {
        "schema": "aoa_xda_graph_receipt_v1",
        "run_id": args.run,
        "profile_id": args.profile,
        "graph_path": str(graph_path),
        "node_count": graph.get("node_count"),
        "edge_count": graph.get("edge_count"),
        "claim_stats": graph.get("claim_stats", {}),
        "created_at": _now(),
        "network_touched": False,
        "read_only": True,
    }
    receipt_path = _write_receipt(roots.artifact / "receipts", args.run, "graph", receipt)
    _emit({"status": "ok", "receipt": str(receipt_path), **receipt})
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    packet = query_keyword_index(roots.artifact / "indexes" / args.run / "keyword_index.json", args.query, limit=args.limit)
    _emit({"status": "ok", **packet, "network_touched": False})
    return 0


def cmd_query_graph(args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    packet = query_graph_packet(
        roots.artifact / "indexes" / args.run / "keyword_index.json",
        roots.artifact / "graphs" / args.run / "graph.json",
        args.query,
        limit=args.limit,
    )
    _emit({"status": "ok", **packet, "network_touched": False})
    return 0


def cmd_answer(args: argparse.Namespace) -> int:
    roots = StorageRoots.from_env(find_repo_root())
    packet = query_graph_packet(
        roots.artifact / "indexes" / args.run / "keyword_index.json",
        roots.artifact / "graphs" / args.run / "graph.json",
        args.query,
        limit=args.limit,
    )
    answer = render_answer_packet(packet, limit=args.limit)
    _emit({"status": "ok", **answer, "network_touched": False})
    return 0


def cmd_eval_claim_relations(args: argparse.Namespace) -> int:
    report = run_claim_relation_suite(Path(args.suite), find_repo_root())
    _emit(report)
    return 0 if report.get("status") == "pass" else 1


def cmd_eval_answer_packets(args: argparse.Namespace) -> int:
    report = run_answer_packet_suite(Path(args.suite), find_repo_root())
    _emit(report)
    return 0 if report.get("status") == "pass" else 1


def _missing_roots(roots: StorageRoots) -> int:
    _emit({"schema": "aoa_xda_missing_storage_roots_v1", "status": "error", "missing": roots.missing(), "network_touched": False})
    return 1


def _write_receipt(receipt_dir: Path, run_id: str, kind: str, payload: dict[str, object]) -> Path:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    path = receipt_dir / f"{run_id}__{kind}.json"
    latest = receipt_dir / f"latest_{kind}.json"
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    return path


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
