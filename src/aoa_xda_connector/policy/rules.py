"""Source route policy for public XDA pages."""

from __future__ import annotations

from urllib.parse import urlparse


FORBIDDEN_MARKERS = (
    "/login",
    "/account",
    "/conversations",
    "/attachments",
    "/search",
    "/api/",
    "/posts/",
    "reply",
    "internal-search",
)


def route_decision(url: str) -> dict[str, object]:
    parsed = urlparse(url)
    lowered = url.lower()
    reasons: list[str] = []
    allowed = parsed.scheme in {"http", "https"} and parsed.netloc.lower().endswith("xdaforums.com")
    if not allowed:
        reasons.append("not an xdaforums.com public URL")
    if any(marker in lowered for marker in FORBIDDEN_MARKERS):
        allowed = False
        reasons.append("forbidden login/account/private/search/write/download route")
    if "/t/" not in parsed.path and "/f/" not in parsed.path:
        allowed = False
        reasons.append("not a public thread or forum route")
    if parsed.query:
        reasons.append("query string requires manual review")
    return {
        "schema": "aoa_xda_route_decision_v1",
        "url": url,
        "allowed": allowed,
        "reasons": reasons,
        "read_only": True,
        "network_default": "disabled",
    }
