import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


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
