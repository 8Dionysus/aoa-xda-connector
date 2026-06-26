"""Repository and environment configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ENV_DATA_ROOT = "CONNECTOR_DATA_ROOT"
ENV_CACHE_ROOT = "CONNECTOR_CACHE_ROOT"
ENV_ARTIFACT_ROOT = "CONNECTOR_ARTIFACT_ROOT"
LOCAL_STATE_DIR = ".connector-state"


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "connector").is_dir():
            return candidate
    return current


@dataclass(frozen=True)
class StorageRoots:
    data: Path | None
    cache: Path | None
    artifact: Path | None
    mode: str = "environment"

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> "StorageRoots":
        root = (repo_root or find_repo_root()).resolve()
        if any(os.environ.get(name) for name in [ENV_DATA_ROOT, ENV_CACHE_ROOT, ENV_ARTIFACT_ROOT]):
            return cls(
                data=_env_path(ENV_DATA_ROOT, root),
                cache=_env_path(ENV_CACHE_ROOT, root),
                artifact=_env_path(ENV_ARTIFACT_ROOT, root),
                mode="environment",
            )
        state_root = root / LOCAL_STATE_DIR
        return cls(
            data=state_root / "data",
            cache=state_root / "cache",
            artifact=state_root / "artifacts",
            mode="repo_local_default",
        )

    def as_dict(self) -> dict[str, str | None]:
        return {
            ENV_DATA_ROOT: str(self.data) if self.data else None,
            ENV_CACHE_ROOT: str(self.cache) if self.cache else None,
            ENV_ARTIFACT_ROOT: str(self.artifact) if self.artifact else None,
        }

    def missing(self) -> list[str]:
        missing: list[str] = []
        if self.data is None:
            missing.append(ENV_DATA_ROOT)
        if self.cache is None:
            missing.append(ENV_CACHE_ROOT)
        if self.artifact is None:
            missing.append(ENV_ARTIFACT_ROOT)
        return missing


def _env_path(name: str, repo_root: Path) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def path_is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
