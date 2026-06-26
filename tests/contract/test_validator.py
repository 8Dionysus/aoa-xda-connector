import json
import subprocess
import sys


def test_validator_passes() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/validate_connector.py"],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
