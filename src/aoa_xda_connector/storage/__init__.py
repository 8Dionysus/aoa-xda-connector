"""Configured storage route helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from aoa_xda_connector.config import LOCAL_STATE_DIR, StorageRoots, path_is_inside


def create_storage_roots(roots: StorageRoots) -> list[str]:
    created: list[str] = []
    for path in [roots.data, roots.cache, roots.artifact]:
        if path is None:
            continue
        path.mkdir(parents=True, exist_ok=True)
        created.append(str(path))
    return created


def storage_warnings(repo_root: Path, roots: StorageRoots | None = None) -> list[str]:
    roots = roots or StorageRoots.from_env(repo_root)
    local_state_root = repo_root / LOCAL_STATE_DIR
    warnings: list[str] = []
    for name, value in roots.as_dict().items():
        if value is None:
            warnings.append(f"{name} is not set")
            continue
        path = Path(value)
        if path_is_inside(path, repo_root) and not path_is_inside(path, local_state_root):
            warnings.append(f"{name} points inside the repository: {path}")
    return warnings


def storage_status(repo_root: Path, roots: StorageRoots, *, measure: bool = False) -> dict[str, object]:
    root_reports = {
        "data": _root_status(repo_root, roots.data, measure=measure),
        "cache": _root_status(repo_root, roots.cache, measure=measure),
        "artifact": _root_status(repo_root, roots.artifact, measure=measure),
    }
    warnings = storage_warnings(repo_root, roots)
    init_required = any(not report.get("exists") for report in root_reports.values())
    return {
        "schema": "aoa_xda_storage_status_v1",
        "status": "warn" if warnings or init_required else "ok",
        "storage_mode": roots.mode,
        "local_state_dir": LOCAL_STATE_DIR,
        "storage_roots": roots.as_dict(),
        "roots": root_reports,
        "warnings": warnings,
        "init_required": init_required,
        "measure": measure,
        "receipts": _receipt_status(roots.artifact),
        "network_touched": False,
    }


def _root_status(repo_root: Path, path: Path | None, *, measure: bool) -> dict[str, object]:
    if path is None:
        return {
            "path": None,
            "exists": False,
            "is_dir": False,
            "inside_repository": False,
            "inside_repo_local_state": False,
            "size_bytes": None,
            "file_count": None,
            "free_bytes": None,
        }
    exists = path.exists()
    report: dict[str, object] = {
        "path": str(path),
        "exists": exists,
        "is_dir": path.is_dir(),
        "inside_repository": path_is_inside(path, repo_root),
        "inside_repo_local_state": path_is_inside(path, repo_root / LOCAL_STATE_DIR),
        "size_bytes": None,
        "file_count": None,
        "free_bytes": None,
    }
    disk_anchor = path if exists else _nearest_existing_parent(path)
    if disk_anchor is not None:
        usage = shutil.disk_usage(disk_anchor)
        report["free_bytes"] = usage.free
        report["total_bytes"] = usage.total
    if measure and path.is_dir():
        measured = _measure_tree(path)
        report["size_bytes"] = measured["size_bytes"]
        report["file_count"] = measured["file_count"]
    return report


def _nearest_existing_parent(path: Path) -> Path | None:
    for candidate in [path, *path.parents]:
        if candidate.exists():
            return candidate
    return None


def _measure_tree(root: Path) -> dict[str, int]:
    size = 0
    file_count = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            size += path.stat().st_size
        except OSError:
            continue
        file_count += 1
    return {"size_bytes": size, "file_count": file_count}


def _receipt_status(artifact_root: Path | None) -> dict[str, object]:
    if artifact_root is None:
        return {"root": None, "exists": False, "latest": {}}
    receipt_dir = artifact_root / "receipts"
    latest: dict[str, object] = {}
    if receipt_dir.is_dir():
        for path in sorted(receipt_dir.glob("latest_*.json")):
            kind = path.stem.removeprefix("latest_")
            latest[kind] = _read_receipt_summary(path)
    return {"root": str(receipt_dir), "exists": receipt_dir.is_dir(), "latest": latest}


def _read_receipt_summary(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"path": str(path), "error": str(exc)}
    return {
        "path": str(path),
        "schema": payload.get("schema"),
        "run_id": payload.get("run_id"),
        "profile_id": payload.get("profile_id"),
        "network_touched": payload.get("network_touched"),
    }
