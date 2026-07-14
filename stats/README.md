# aoa-xda-connector local stats port

This directory exposes statistical questions whose domain meaning belongs to
the XDA connector. It uses the shared `aoa-stats` grammar without moving XDA
source policy, normalized content, claim truth, graph semantics, eval verdicts,
or runtime state into the central stats organ.

## Current reference measurement

| Measurement | Reference value |
| --- | --- |
| `aoa-xda-connector/starter-actionable-entity-claim-traceability-ratio` | `10 / 10` |

The question is: what fraction of normalized actionable entity occurrences in
the canonical public XDA starter topic are materialized as claims with matching
source identity and a direct source-to-claim relation?

The population is a census of ten unique `root_action`, `recovery_action`,
`warning`, and `status` entity occurrences emitted by the normalizer. The
numerator contains only claims whose source post, semantic kind, and action
match the normalized occurrence and whose graph node and source relation retain
the same source identity. The aggregate uses a ratio of sums across the four
bounded actionable kinds.

A missing claim or source relation is an observed gap, and a valid graph with
no relevant claims is an observed zero. Malformed, empty, duplicate,
unexpected, or contradictory normalized or graph evidence is unknown.

## Evidence posture

The packet is a public, reference-only snapshot derived from the committed
starter fixture, normalizer, claim extractor, and graph builder at source
revision `0bce839df06edba50553fb34ca758716792b05f6`. It contains aggregate counts
and portable source references, not post text, authors, post or claim
identities, source URLs, graph edges, configured storage, live XDA state, or
eval output. Terminal progress means only that the ten-occurrence fixture
census was processed.

## Authority

The ratio describes structural traceability in one deterministic starter
pipeline. It does not establish parser or entity completeness, claim truth,
cross-claim relation quality, answer quality, live-source coverage, connector
readiness, eval success, proof verdicts, or runtime health.

## Surfaces

- `port.manifest.json` declares the owner-local question and measurement.
- `packets/` records the evidence-linked reference observation.
- the normalizer owns the actionable occurrence population;
- claim extraction and graph construction own claim and source-relation
  materialization;
- `aoa-stats` owns shared validation and cross-owner composition.
