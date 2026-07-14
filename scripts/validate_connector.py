#!/usr/bin/env python3
"""Validate the GitHub-publishable XDA connector skeleton."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


COMMAND_FENCE_LANGUAGES = {
    "bash",
    "sh",
    "shell",
    "console",
    "terminal",
    "powershell",
    "cmd",
}
COMMAND_LINE_RE = re.compile(
    r"^\s*(?:\$\s+|[A-Z][A-Z0-9_]*=|python(?:3)?\s+|pytest(?:\s|$)|"
    r"aoa-xda(?:\s|$)|pip(?:3)?\s+|uv\s+|git\s+|export\s+)",
    re.IGNORECASE,
)


REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "CHARTER.md",
    "BOUNDARIES.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "pyproject.toml",
    ".env.example",
    ".gitignore",
    ".connector-state/AGENTS.md",
    ".connector-state/README.md",
    "connector/SOURCE_POLICY.md",
    "connector/STORAGE_POLICY.md",
    "connector/manifests/connector_manifest.yaml",
    "connector/manifests/route_allowlist.yaml",
    "connector/manifests/artifact_classes.yaml",
    "connector/profiles/pixel-8-pro-husky.yaml",
    "connector/seeds/pixel_8_pro_husky_threads.yaml",
    "connector/fixtures/html/xda_pixel_8_pro_husky_root_thread.html",
    "docs/ARCHITECTURE.md",
    "docs/INSTALL.md",
    "docs/AGENT_INSTALL_ROUTE.md",
    "docs/QUERY_MODEL.md",
    "docs/GRAPH_MODEL.md",
    "docs/RUNTIME_CONTRACT.md",
    "docs/MCP_ROLLOUT.md",
    "docs/STARTER_PROOF.md",
    "docs/CONNECTOR_FAMILY_CLAIM_CONTRACT.md",
    "docs/decisions/README.md",
    "docs/decisions/AOA-XDA-D-0001-second-source-connector-proof.md",
    "evals/AGENTS.md",
    "evals/PORT.yaml",
    "evals/suites/README.md",
    "evals/suites/connector-family-claim-runtime.suite.md",
    "evals/suites/starter_claim_conflict_relations.json",
    "evals/suites/starter_claim_answer_packets.json",
    "kag/AGENTS.md",
    "kag/README.md",
    "kag/manifest.json",
    "kag/nodes/source_home.json",
    "kag/nodes/storage_boundary.json",
    "kag/edges/source_routes_to_storage_boundary.json",
    "kag/indexes/source_inventory.json",
    "kag/indexes/source_surface_index.json",
    "kag/projections/source_return.json",
    "kag/receipts/validation_receipt.json",
    "scripts/validate_local_stats_port.py",
    "stats/AGENTS.md",
    "stats/README.md",
    "stats/port.manifest.json",
    "stats/packets/starter-actionable-entity-claim-traceability-ratio.reference.json",
    "src/aoa_xda_connector/cli.py",
]

REQUIRED_DIRS = [
    ".connector-state",
    ".connector-state/data",
    ".connector-state/cache",
    ".connector-state/artifacts",
    "src/aoa_xda_connector/parse",
    "src/aoa_xda_connector/normalize",
    "src/aoa_xda_connector/index",
    "src/aoa_xda_connector/graph",
    "src/aoa_xda_connector/claims",
    "src/aoa_xda_connector/answer",
    "src/aoa_xda_connector/query",
    "src/aoa_xda_connector/evaluation",
    "src/aoa_xda_connector/storage",
    "tests/unit",
    "tests/contract",
    "tests/integration",
    "evals/intake",
    "evals/reports",
    "kag",
    "kag/nodes",
    "kag/edges",
    "kag/indexes",
    "kag/projections",
    "kag/receipts",
    "stats",
    "stats/packets",
]

REQUIRED_SCHEMAS = [
    "crawl_receipt.schema.json",
    "normalized_topic.schema.json",
    "normalized_post.schema.json",
    "evidence_packet.schema.json",
    "answer_packet.schema.json",
    "materialize_receipt.schema.json",
    "index_manifest.schema.json",
    "graph_node.schema.json",
    "graph_edge.schema.json",
    "claim.schema.json",
    "claim_relation.schema.json",
    "conflict_report.schema.json",
    "freshness_report.schema.json",
    "applicability_report.schema.json",
    "warning_report.schema.json",
]

REQUIRED_GITIGNORE = [
    ".connector-state/*",
    "!.connector-state/README.md",
    "!.connector-state/AGENTS.md",
    "!.connector-state/data/",
    "!.connector-state/cache/",
    "!.connector-state/artifacts/",
    ".connector-state/data/*",
    ".connector-state/cache/*",
    ".connector-state/artifacts/*",
    "!.connector-state/data/.gitkeep",
    "!.connector-state/cache/.gitkeep",
    "!.connector-state/artifacts/.gitkeep",
    "data/",
    "cache/",
    "artifacts/",
    "raw/",
    "indexes/",
    "vectors/",
    "graphs/",
    "exports/full/",
    "*.sqlite",
    "*.sqlite3",
    "*.parquet",
    "*.qdrant/",
    "*.lancedb/",
]

FORBIDDEN_HEAVY_ROOTS = {"data", "cache", "artifacts", "raw", "indexes", "vectors", "graphs", "exports"}
IGNORED_LOCAL_CACHE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv"}
IGNORED_REPO_SCAN_ROOTS = {".connector-state", ".deps"}
ALLOWED_KAG_RECORD_DIRS = {("kag", "indexes")}


def _is_allowed_kag_record_path(path: Path, rel_parts: tuple[str, ...]) -> bool:
    if len(rel_parts) == 2 and tuple(rel_parts) in ALLOWED_KAG_RECORD_DIRS:
        return True
    return (
        len(rel_parts) == 3
        and tuple(rel_parts[:2]) in ALLOWED_KAG_RECORD_DIRS
        and path.is_file()
        and path.suffix == ".json"
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (repo_root / rel).is_file():
            errors.append(f"missing required file: {rel}")
    for rel in REQUIRED_DIRS:
        if not (repo_root / rel).is_dir():
            errors.append(f"missing required directory: {rel}")

    schema_dir = repo_root / "connector" / "schemas"
    for name in REQUIRED_SCHEMAS:
        path = schema_dir / name
        if not path.is_file():
            errors.append(f"missing schema: connector/schemas/{name}")
        else:
            _load_json(path, errors)

    for path in [
        *repo_root.glob("connector/fixtures/**/*.json"),
        *repo_root.glob("evals/suites/**/*.json"),
        *repo_root.glob("kag/**/*.json"),
        *repo_root.glob("stats/**/*.json"),
    ]:
        _load_json(path, errors)

    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8") if (repo_root / ".gitignore").exists() else ""
    for pattern in REQUIRED_GITIGNORE:
        if pattern not in gitignore:
            errors.append(f".gitignore missing heavy-data pattern: {pattern}")

    for rel in FORBIDDEN_HEAVY_ROOTS:
        if (repo_root / rel).exists():
            errors.append(f"heavy artifact path exists inside repository: {rel}")

    for path in repo_root.rglob("*"):
        if ".git" in path.parts:
            continue
        rel_parts = path.relative_to(repo_root).parts
        if _is_ignored_repo_scan_path(rel_parts):
            continue
        if _is_allowed_kag_record_path(path, rel_parts):
            continue
        if path.is_dir() and path.name in FORBIDDEN_HEAVY_ROOTS:
            errors.append(f"forbidden artifact directory exists inside repository: {path.relative_to(repo_root)}")

    _check_text(repo_root, errors, warnings)
    _check_eval_port(repo_root, errors)
    _check_markdown_command_hygiene(repo_root, errors)

    payload = {
        "schema": "aoa_xda_connector_validation_v1",
        "status": "ok" if not errors else "error",
        "repo_root": str(repo_root),
        "errors": errors,
        "warnings": warnings,
        "checked": {
            "required_files": len(REQUIRED_FILES),
            "required_dirs": len(REQUIRED_DIRS),
            "schemas": len(REQUIRED_SCHEMAS),
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _load_json(path: Path, errors: list[str]) -> None:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid json {path}: {exc}")


def _is_ignored_repo_scan_path(rel_parts: tuple[str, ...]) -> bool:
    return (
        bool(rel_parts and rel_parts[0] in IGNORED_REPO_SCAN_ROOTS)
        or any(part in IGNORED_LOCAL_CACHE_DIR_NAMES for part in rel_parts)
    )


def _check_markdown_command_hygiene(repo_root: Path, errors: list[str]) -> None:
    """Keep executable command blocks in their owners or an applicable AGENTS route."""

    for path in sorted(repo_root.rglob("*.md")):
        if path.name == "AGENTS.md" or ".git" in path.parts or ".deps" in path.parts:
            continue
        relative = path.relative_to(repo_root)
        fence_marker = ""
        fence_language = ""
        fence_start = 0
        body: list[str] = []
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            stripped = line.lstrip()
            if not fence_marker:
                if stripped.startswith("```") or stripped.startswith("~~~"):
                    fence_marker = stripped[:3]
                    language = stripped[3:].strip().casefold()
                    fence_language = language.split(maxsplit=1)[0] if language else ""
                    fence_start = line_number
                    body = []
                continue
            if stripped.startswith(fence_marker):
                command_block = fence_language in COMMAND_FENCE_LANGUAGES or any(
                    COMMAND_LINE_RE.match(item) for item in body
                )
                if command_block:
                    errors.append(f"command block outside AGENTS.md: {relative}:{fence_start}")
                fence_marker = ""
                fence_language = ""
                fence_start = 0
                body = []
            else:
                body.append(line)
        if fence_marker:
            errors.append(f"unterminated Markdown fence: {relative}:{fence_start}")


def _check_text(repo_root: Path, errors: list[str], warnings: list[str]) -> None:
    source_policy = (repo_root / "connector" / "SOURCE_POLICY.md").read_text(encoding="utf-8")
    route_policy = (repo_root / "connector" / "manifests" / "route_allowlist.yaml").read_text(encoding="utf-8")
    storage_policy = (repo_root / "connector" / "STORAGE_POLICY.md").read_text(encoding="utf-8")
    runtime_contract = (repo_root / "docs" / "RUNTIME_CONTRACT.md").read_text(encoding="utf-8")
    doctrine = (repo_root / "docs" / "CONNECTOR_FAMILY_CLAIM_CONTRACT.md").read_text(encoding="utf-8")

    for token in ["login", "account", "conversations", "attachments", "download", "write", "reply", "internal search"]:
        if token not in source_policy.casefold():
            errors.append(f"source policy missing denied token: {token}")

    for token in ["/login", "/account", "/conversations", "/attachments", "/search", "reply", "internal-search"]:
        if token not in route_policy:
            errors.append(f"route allowlist missing denied token: {token}")

    for var in ["CONNECTOR_DATA_ROOT", "CONNECTOR_CACHE_ROOT", "CONNECTOR_ARTIFACT_ROOT"]:
        if var not in storage_policy or var not in (repo_root / ".env.example").read_text(encoding="utf-8"):
            errors.append(f"storage root variable missing from docs/env: {var}")

    for token in [
        "aoa-xda-connector-mcp",
        "agent_answer",
        "evidence_chain",
        "conflict_report",
        "freshness_report",
        "applicability_report",
        "warning_report",
        "network_touched=false",
        "read_only=true",
        "internal-search source route",
    ]:
        if token not in runtime_contract:
            errors.append(f"runtime contract missing token: {token}")

    for token in ["claim", "claim_relation", "insufficient_evidence", "warning_report", "freshness_report"]:
        if token not in doctrine:
            errors.append(f"connector-family doctrine missing token: {token}")

    if "robots" in source_policy.casefold():
        warnings.append("robots policy is advisory only; keep hard source boundaries explicit")


def _check_eval_port(repo_root: Path, errors: list[str]) -> None:
    port = (repo_root / "evals" / "PORT.yaml").read_text(encoding="utf-8")
    for token in [
        "schema_version: local_eval_port_v1",
        "owner_repo: aoa-xda-connector",
        "proof_owner_repo: aoa-evals",
        "no verdict, scoring, regression, or proof doctrine authority",
    ]:
        if token not in port:
            errors.append(f"eval port missing boundary token: {token}")

    expected_suites = {
        "starter_claim_conflict_relations.json": "aoa_xda_claim_graph_eval_suite_v1",
        "starter_claim_answer_packets.json": "aoa_xda_answer_eval_suite_v1",
    }
    for suite_name, schema in expected_suites.items():
        suite = json.loads((repo_root / "evals" / "suites" / suite_name).read_text(encoding="utf-8"))
        if suite.get("schema") != schema:
            errors.append(f"{suite_name} has unexpected schema")
        if suite.get("proof_owner_repo") != "aoa-evals":
            errors.append(f"{suite_name} must keep aoa-evals as proof owner")
        if not suite.get("cases"):
            errors.append(f"{suite_name} must include at least one case")


if __name__ == "__main__":
    sys.exit(main())
