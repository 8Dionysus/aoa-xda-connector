# Starter Proof

The starter proof uses a sanitized XDA-like fixture for Pixel 8 Pro / husky.

It proves:

- parser extracts thread title, public author labels, post IDs, timestamps,
  code excerpts, links, and quote-stripped text
- normalizer extracts Android device entities
- claim extractor produces method, warning, and status claims
- graph builder emits claim relation semantics
- answer packet includes conflict, freshness, applicability, and warning
  reports
- eval suites catch warning-supported answers, stale-method demotion,
  applicability, conflict/supersession, and insufficient evidence

It does not prove:

- full XDA coverage
- live crawling readiness
- attachment handling
- private/account route support
- completeness for Pixel 8 Pro

The root `stats/` port records the narrower reference observation that all ten
normalized actionable entity occurrences in this fixture are represented by
source-traceable graph claims. This is structural traceability, not a claim of
parser completeness, semantic correctness, relation quality, eval success, or
live XDA coverage.
