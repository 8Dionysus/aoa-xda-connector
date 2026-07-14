# AGENTS.md

Route card for owner-local statistical questions in `aoa-xda-connector`.
Read the root `AGENTS.md` first.

## Applies To

Everything under `stats/`.

## Role

This directory owns bounded statistics over normalized XDA and claim-graph
evidence. Shared measurement grammar and cross-owner composition remain owned
by `aoa-stats`; parser, claim, graph, and source-policy meaning remain owned by
this repository; eval verdicts remain owned by `aoa-evals`; and live XDA data
remains outside Git in configured storage.

## Read Before Editing

1. Root `AGENTS.md`, `CHARTER.md`, and `BOUNDARIES.md`.
2. `connector/SOURCE_POLICY.md` and `connector/STORAGE_POLICY.md`.
3. The starter fixture, normalizer, claim extractor, and graph builder relevant
   to the measure.
4. `evals/AGENTS.md` when the same evidence is also consumed by an eval.
5. `stats/README.md`, `stats/port.manifest.json`, and the central contracts
   under `aoa-stats/stats/`.

## Boundaries

- The reference population is the non-empty set of unique `root_action`,
  `recovery_action`, `warning`, and `status` entity occurrences emitted for the
  canonical public starter topic.
- An occurrence enters the numerator only when the graph contains the matching
  source-post claim and the required source-to-claim relation.
- A missing matching claim or source relation is an observed traceability gap.
  A valid graph without relevant claims is an observed zero.
- Malformed, empty, duplicate, unexpected, or contradictory normalized or
  graph evidence is unknown.
- Packets must not carry post text, authors, post or claim identities, source
  URLs, graph edges, operator-local state, or live XDA content.
- The reference packet is weaker than the fixture, normalizer, claim extractor,
  graph builder, executable audits, eval results, and live XDA evidence.
- The ratio does not prove parser or entity completeness, claim truth,
  cross-claim relation quality, answer quality, eval success, live coverage,
  connector readiness, proof, or runtime health.

## Validation

Inspect the normalized starter topic, graph, and packet first. The port
validator requires a compatible `aoa-stats` checkout through `AOA_STATS_ROOT`,
`.deps/aoa-stats`, or the workspace sibling route. Then run:

```bash
AOA_STATS_ROOT=/path/to/aoa-stats python scripts/validate_local_stats_port.py
PYTHONPATH=src python -m pytest -q tests/unit/test_local_stats_port.py
```

Use the root route for repository-wide validation.

## Closeout

Report the aggregate and per-kind counts, manual positive and negative cases,
unknown handling, packet posture, central validation, and repository
validation.
