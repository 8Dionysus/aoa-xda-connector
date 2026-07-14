import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_validator_module():
    path = REPO_ROOT / "scripts" / "validate_connector.py"
    spec = importlib.util.spec_from_file_location("validate_connector", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validator_passes() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/validate_connector.py"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"


def test_validator_rejects_malformed_kag_json() -> None:
    manifest = REPO_ROOT / "kag" / "manifest.json"
    original = manifest.read_text(encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, "scripts/validate_connector.py"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        assert completed.returncode == 0
        manifest.write_text("{not-json", encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "scripts/validate_connector.py"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
    finally:
        manifest.write_text(original, encoding="utf-8")

    assert completed.returncode == 1, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert any("invalid json" in error and "kag/manifest.json" in error for error in payload["errors"])


def test_markdown_hygiene_rejects_command_fence_outside_agents(tmp_path: Path) -> None:
    validator = load_validator_module()
    (tmp_path / "README.md").write_text(
        "# Readme\n\n```bash\npython scripts/validate_connector.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS.md\n\n```bash\npython scripts/validate_connector.py\n```\n",
        encoding="utf-8",
    )
    errors: list[str] = []

    validator._check_markdown_command_hygiene(tmp_path, errors)

    assert errors == ["command block outside AGENTS.md: README.md:3"]


def test_dependency_checkout_is_outside_owner_artifact_scan() -> None:
    validator = load_validator_module()

    assert validator._is_ignored_repo_scan_path(
        (".deps", "aoa-stats", "kag", "indexes")
    ) is True
    assert validator._is_ignored_repo_scan_path(("kag", "indexes")) is False
