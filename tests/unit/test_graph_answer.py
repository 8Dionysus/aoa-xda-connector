from pathlib import Path

from aoa_xda_connector.answer import render_answer_packet
from aoa_xda_connector.graph import build_graph
from aoa_xda_connector.index import build_keyword_index
from aoa_xda_connector.normalize import normalize_snapshot
from aoa_xda_connector.query import query_graph_packet


FIXTURE_URL = "https://xdaforums.com/t/pixel-8-pro-husky-root-recovery-proof.4633839/"


def _build(tmp_path: Path) -> tuple[Path, Path]:
    fixture = Path("connector/fixtures/html/xda_pixel_8_pro_husky_root_thread.html")
    normalized_dir = tmp_path / "normalized"
    normalize_snapshot(fixture, FIXTURE_URL, normalized_dir)
    index_path = build_keyword_index(normalized_dir, tmp_path / "index")
    graph_path = build_graph(normalized_dir, tmp_path / "graph")
    return index_path, graph_path


def test_graph_contains_claim_relations(tmp_path: Path) -> None:
    _, graph_path = _build(tmp_path)
    graph_text = graph_path.read_text(encoding="utf-8")
    assert "aoa_connector_claim_v1" in graph_text
    assert "source_warns_about_claim" in graph_text
    assert "claim_supersedes_claim" in graph_text
    assert "claim_contradicts_claim" in graph_text
    assert "method_requires_condition" in graph_text


def test_answer_packet_reports_warning_and_freshness(tmp_path: Path) -> None:
    index_path, graph_path = _build(tmp_path)
    packet = query_graph_packet(index_path, graph_path, "Pixel 8 Pro husky warning vendor_boot bootloop Android 15")
    answer = render_answer_packet(packet)
    assert answer["schema"] == "aoa_connector_answer_packet_v1"
    assert answer["network_touched"] is False
    assert answer["read_only"] is True
    assert answer["answer_report"]["answer_status"] == "answered"
    assert answer["warning_report"]["status"] == "warning_supported"
    assert answer["conflict_report"]["status"] == "conflict_detected"
    assert answer["evidence_chain"][0]["claim_ids"]
    assert answer["evidence_chain"][0]["post_id"]


def test_answer_packet_insufficient_evidence(tmp_path: Path) -> None:
    index_path, graph_path = _build(tmp_path)
    packet = query_graph_packet(index_path, graph_path, "Galaxy S99 unicorn modem unlock XDA answer")
    answer = render_answer_packet(packet)
    assert answer["answer_report"]["answer_status"] == "insufficient_evidence"
    assert answer["conflict_report"]["status"] == "insufficient_evidence"
    assert answer["freshness_report"]["status"] == "insufficient_evidence"
    assert answer["warning_report"]["status"] == "insufficient_evidence"
