import json
import os
import subprocess
import sys


def _run(*args: str, env: dict[str, str] | None = None) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-m", "aoa_xda_connector.cli", *args],
        check=True,
        text=True,
        capture_output=True,
        env=env,
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


def test_cli_sources_registry_plans_xda_crawl_scope(tmp_path) -> None:
    env = os.environ.copy()
    env["CONNECTOR_DATA_ROOT"] = str(tmp_path / "data")
    env["CONNECTOR_CACHE_ROOT"] = str(tmp_path / "cache")
    env["CONNECTOR_ARTIFACT_ROOT"] = str(tmp_path / "artifacts")

    thread = _run(
        "sources",
        "add",
        "https://xdaforums.com/t/pixel-8-pro-husky-root-recovery-proof.4633839/",
        "--kind",
        "thread",
        "--tags",
        "pixel,root",
        "--trust-score",
        "0.8",
        env=env,
    )
    assert thread["status"] == "ok"
    assert thread["source"]["access"] == "public"
    listed = _run("sources", "list", "--tag", "pixel", env=env)
    assert listed["selected_count"] == 1
    plan = _run("sources", "plan", "--run", "pytest-xda-sources", "--limit", "5", env=env)
    assert plan["schema"] == "aoa_xda_source_crawl_plan_v1"
    assert plan["steps"][0]["operation"] == "crawl"
    assert plan["network_touched"] is False
