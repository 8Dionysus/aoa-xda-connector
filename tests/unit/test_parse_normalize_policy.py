from pathlib import Path

from aoa_xda_connector.normalize import normalize_snapshot
from aoa_xda_connector.parse import decode_html, extract_posts, extract_title
from aoa_xda_connector.policy.rules import route_decision


FIXTURE_URL = "https://xdaforums.com/t/pixel-8-pro-husky-root-recovery-proof.4633839/"


def test_parser_strips_quotes_and_keeps_code() -> None:
    fixture = Path("connector/fixtures/html/xda_pixel_8_pro_husky_root_thread.html")
    document = decode_html(fixture.read_bytes())
    posts = extract_posts(document, FIXTURE_URL)
    assert extract_title(document).startswith("[Pixel 8 Pro")
    assert len(posts) == 5
    assert posts[0]["post_id"] == "90000001"
    assert posts[0]["code_excerpts"] == ["fastboot flash init_boot_a patched_init_boot.img"]
    assert "Someone said" not in posts[-1]["text"]
    assert "signature text" not in posts[-1]["text"]


def test_normalizer_extracts_xda_android_entities(tmp_path: Path) -> None:
    fixture = Path("connector/fixtures/html/xda_pixel_8_pro_husky_root_thread.html")
    output = normalize_snapshot(fixture, FIXTURE_URL, tmp_path)
    topic = output.read_text(encoding="utf-8")
    assert "aoa_xda_normalized_topic_v1" in topic
    assert "Pixel 8 Pro" in topic
    assert "husky" in topic
    assert "init_boot.img" in topic
    assert "bootloader_unlocked" in topic
    assert "quote_blocks_stripped" in topic


def test_policy_denies_forbidden_routes() -> None:
    assert route_decision(FIXTURE_URL)["allowed"] is True
    assert route_decision("https://xdaforums.com/search/123")["allowed"] is False
    assert route_decision("https://xdaforums.com/account/")["allowed"] is False
    assert route_decision("https://xdaforums.com/attachments/file.zip")["allowed"] is False
