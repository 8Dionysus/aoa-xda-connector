import json
import subprocess
import sys


def _run(*args: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-m", "aoa_xda_connector.cli", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_cli_materialize_build_and_eval() -> None:
    materialize = _run("materialize", "fixture", "--run", "pytest-fixture")
    assert materialize["network_touched"] is False
    index = _run("build-index", "--run", "pytest-fixture")
    assert index["doc_count"] >= 5
    graph = _run("build-graph", "--run", "pytest-fixture")
    assert graph["claim_stats"]["claim_count"] >= 5
    claim_eval = _run("eval", "claim-relations")
    assert claim_eval["status"] == "pass"
    answer_eval = _run("eval", "answer-packets")
    assert answer_eval["status"] == "pass"
