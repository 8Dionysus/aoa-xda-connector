"""Graph builder for starter normalized XDA records."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from aoa_xda_connector.claims import (
    assign_freshness_windows,
    claim_graph_stats,
    extract_post_claims,
    graph_nodes_for_claims,
    relation_edges_for_claims,
)


def build_graph(normalized_dir: Path, output_dir: Path, profile_id: str = "pixel-8-pro-husky") -> Path:
    nodes: dict[str, dict[str, object]] = {}
    edges: list[dict[str, object]] = []
    claims: list[dict[str, object]] = []
    for topic_path in sorted(normalized_dir.glob("topic-*.json")):
        topic = json.loads(topic_path.read_text(encoding="utf-8"))
        topic_node = f"topic:{topic['thread_id']}"
        nodes[topic_node] = {
            "schema": "aoa_xda_graph_node_v1",
            "node_id": topic_node,
            "kind": "topic",
            "label": topic.get("title", topic["thread_id"]),
            "source_refs": [topic.get("source_url")],
            "confidence": 1.0,
        }
        for post in topic.get("posts", []):
            post_node = f"post:{post['post_id']}"
            source_url = post.get("source_url")
            nodes[post_node] = {
                "schema": "aoa_xda_graph_node_v1",
                "node_id": post_node,
                "kind": "post",
                "label": f"Post {post['post_id']}",
                "source_refs": [source_url],
                "confidence": 1.0,
            }
            _append_edge(edges, "topic_contains_post", topic_node, post_node, source_url, 1.0)
            for entity in post.get("entities", []):
                if not isinstance(entity, dict):
                    continue
                entity_node = _entity_node_id(entity)
                value = str(entity.get("value") or "")
                kind = str(entity.get("kind") or "term")
                nodes.setdefault(
                    entity_node,
                    {
                        "schema": "aoa_xda_graph_node_v1",
                        "node_id": entity_node,
                        "kind": kind,
                        "label": value,
                        "source_refs": [],
                        "confidence": 0.6,
                    },
                )
                if source_url and source_url not in nodes[entity_node]["source_refs"]:
                    nodes[entity_node]["source_refs"].append(source_url)
                _append_edge(edges, "post_mentions_entity", post_node, entity_node, source_url, 0.6)
            claims.extend(extract_post_claims(post, profile_id))

    assign_freshness_windows(claims)
    nodes.update(graph_nodes_for_claims(claims))
    claim_edges = relation_edges_for_claims(claims)
    edges.extend(claim_edges)
    stats = claim_graph_stats(claims, claim_edges)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "graph.json"
    payload = {
        "schema": "aoa_xda_graph_export_v1",
        "profile_id": profile_id,
        "built_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "claim_stats": stats,
        "nodes": list(nodes.values()),
        "edges": edges,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _append_edge(edges: list[dict[str, object]], kind: str, from_node: str, to_node: str, source_url: object, confidence: float) -> None:
    edge_id = f"{from_node}->{to_node}:{kind}"
    if any(edge.get("edge_id") == edge_id for edge in edges):
        return
    edges.append(
        {
            "schema": "aoa_xda_graph_edge_v1",
            "edge_id": edge_id,
            "kind": kind,
            "from_node": from_node,
            "to_node": to_node,
            "source_refs": [str(source_url or "")],
            "confidence": confidence,
        }
    )


def _entity_node_id(entity: dict[str, object]) -> str:
    return f"entity:{entity.get('kind', 'term')}:{entity.get('value', '')}"
