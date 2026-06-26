"""Query helpers over the starter keyword index and claim graph."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

from aoa_xda_connector.claims import CLAIM_RELATION_KINDS
from aoa_xda_connector.index import extract_exact_terms, technical_alias_tokens, tokenize


BM25_K1 = 1.5
BM25_B = 0.75
EXACT_TERM_BOOST = 2.0
RELATION_EDGE_KINDS = set(CLAIM_RELATION_KINDS)


def packet_id_for_query(query: str) -> str:
    digest = hashlib.sha256(query.strip().encode("utf-8")).hexdigest()
    return f"query-{digest[:16]}"


def query_keyword_index(index_path: Path, query: str, limit: int = 5) -> dict[str, object]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    terms = tokenize(query)
    exact_terms = extract_exact_terms(terms)
    technical_terms = technical_alias_tokens(query)
    docs = {doc["doc_id"]: doc for doc in index.get("docs", [])}
    doc_count = max(1, int(index.get("doc_count", len(docs))))
    avg_doc_len = _average_doc_length(docs.values())
    doc_scores: dict[str, dict[str, object]] = {}

    for term in terms:
        hits = index.get("inverted", {}).get(term, [])
        if not hits:
            continue
        idf = math.log(1 + (doc_count - len(hits) + 0.5) / (len(hits) + 0.5))
        for hit in hits:
            doc_id = str(hit["doc_id"])
            doc = docs[doc_id]
            tf = int(hit["count"])
            doc_len = max(1, int(doc.get("tokens", 0)))
            bm25 = idf * ((tf * (BM25_K1 + 1)) / (tf + BM25_K1 * (1 - BM25_B + BM25_B * doc_len / avg_doc_len)))
            entry = doc_scores.setdefault(doc_id, {"bm25": 0.0, "exact": 0.0, "matched_terms": set(), "matched_exact_terms": set()})
            entry["bm25"] += bm25
            entry["matched_terms"].add(term)

    for term in exact_terms:
        for doc_id in index.get("exact", {}).get(term, []):
            entry = doc_scores.setdefault(doc_id, {"bm25": 0.0, "exact": 0.0, "matched_terms": set(), "matched_exact_terms": set()})
            entry["exact"] += EXACT_TERM_BOOST
            entry["matched_exact_terms"].add(term)

    ranked = sorted(doc_scores.items(), key=lambda item: (float(item[1]["bm25"]) + float(item[1]["exact"]), len(item[1]["matched_exact_terms"])), reverse=True)
    results: list[dict[str, object]] = []
    for doc_id, score in ranked[:limit]:
        doc = docs[doc_id]
        matched_terms = sorted(score["matched_terms"])
        matched_exact_terms = sorted(score["matched_exact_terms"])
        text = str(doc.get("text") or "")
        results.append(
            {
                "source_url": doc.get("source_url"),
                "topic_id": doc.get("topic_id"),
                "post_id": doc.get("post_id"),
                "posted_at": doc.get("posted_at"),
                "captured_at": doc.get("captured_at"),
                "chunk_id": doc_id,
                "snippet": _focused_snippet(text, matched_exact_terms + matched_terms),
                "score": round(float(score["bm25"]) + float(score["exact"]), 6),
                "score_breakdown": {"bm25": round(float(score["bm25"]), 6), "exact": round(float(score["exact"]), 6)},
                "matched_terms": matched_terms,
                "matched_exact_terms": matched_exact_terms,
                "matched_specific_terms": sorted(set(matched_terms).intersection(set(exact_terms + technical_terms))),
                "evidence_refs": [doc_id, f"post:{doc.get('post_id')}"],
            }
        )
    return {
        "schema": "aoa_xda_evidence_packet_v1",
        "packet_id": packet_id_for_query(query),
        "query": query,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "query_report": {
            "algorithm": "bm25_exact_v1",
            "unit": index.get("unit", "post"),
            "terms": terms,
            "exact_terms": exact_terms,
            "technical_terms": technical_terms,
        },
        "results": results,
        "policy": {"source": "local_keyword_index", "internal_search_used": False},
    }


def query_graph_packet(index_path: Path, graph_path: Path, query: str, limit: int = 5) -> dict[str, object]:
    packet = query_keyword_index(index_path, query, limit)
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = {str(node.get("node_id")): node for node in graph.get("nodes", [])}
    edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]
    for rank, result in enumerate(packet.get("results", []), start=1):
        result["keyword_rank"] = rank
        result["graph_context"] = _graph_context_for_result(result, nodes, edges)
    packet["policy"]["source"] = "local_keyword_index_plus_graph"
    packet["graph_report"] = {
        "graph_path": str(graph_path),
        "node_count": graph.get("node_count", 0),
        "edge_count": graph.get("edge_count", 0),
        "claim_stats": graph.get("claim_stats", {}),
        "relation_edge_kinds": sorted({str(edge.get("kind")) for edge in edges if str(edge.get("kind")) in RELATION_EDGE_KINDS}),
    }
    return packet


def _graph_context_for_result(result: dict[str, object], nodes: dict[str, dict[str, object]], edges: list[dict[str, object]]) -> dict[str, object]:
    post_node = f"post:{result.get('post_id')}"
    source_edges = [edge for edge in edges if edge.get("from_node") == post_node or edge.get("to_node") == post_node]
    claim_ids = sorted(
        {
            str(edge.get("to_node"))
            for edge in source_edges
            if str(edge.get("to_node", "")).startswith("claim:")
        }
        | {
            str(edge.get("from_node"))
            for edge in source_edges
            if str(edge.get("from_node", "")).startswith("claim:")
        }
    )
    related_edges = [
        edge
        for edge in edges
        if edge.get("kind") in RELATION_EDGE_KINDS
        and (edge.get("from_node") in claim_ids or edge.get("to_node") in claim_ids or _source_refs_include(edge, str(result.get("source_url") or "")))
    ]
    endpoint_ids = set(claim_ids)
    for edge in related_edges:
        endpoint_ids.add(str(edge.get("from_node")))
        endpoint_ids.add(str(edge.get("to_node")))
    return {
        "post_node_id": post_node,
        "claim_node_ids": claim_ids,
        "claim_nodes": [_node_summary(nodes[node_id]) for node_id in claim_ids if node_id in nodes],
        "relation_edges": [_edge_summary(edge) for edge in related_edges],
        "relation_kinds": sorted({str(edge.get("kind")) for edge in related_edges}),
        "context_nodes": [_node_summary(nodes[node_id]) for node_id in sorted(endpoint_ids) if node_id in nodes],
    }


def _average_doc_length(docs: object) -> float:
    values = [max(1, int(doc.get("tokens", 0))) for doc in docs if isinstance(doc, dict)]
    return sum(values) / len(values) if values else 1.0


def _focused_snippet(text: str, needles: list[str], radius: int = 190) -> str:
    lowered = text.casefold()
    positions = [lowered.find(needle.casefold()) for needle in needles if needle and lowered.find(needle.casefold()) >= 0]
    if not positions:
        return text[: radius * 2]
    start = max(0, min(positions) - radius)
    end = min(len(text), min(positions) + radius)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _node_summary(node: dict[str, object]) -> dict[str, object]:
    return {
        "node_id": node.get("node_id"),
        "kind": node.get("kind"),
        "label": node.get("label"),
        "source_refs": node.get("source_refs", []),
        "claim": node.get("claim"),
    }


def _edge_summary(edge: dict[str, object]) -> dict[str, object]:
    return {
        "edge_id": edge.get("edge_id"),
        "kind": edge.get("kind"),
        "from_node": edge.get("from_node"),
        "to_node": edge.get("to_node"),
        "source_refs": edge.get("source_refs", []),
        "source_post_ids": edge.get("source_post_ids", []),
        "confidence": edge.get("confidence"),
        "relation_reason": edge.get("relation_reason"),
    }


def _source_refs_include(edge: dict[str, object], source_url: str) -> bool:
    return source_url in [str(item) for item in edge.get("source_refs", [])]
