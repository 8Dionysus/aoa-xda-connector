# Boundaries

## In Scope

- Public XDA forum/thread/post pages.
- Bounded starter profiles and seed manifests.
- Sanitized fixtures that preserve source shape without storing user-private
  data.
- Local indexes, graphs, claims, and answer packets built from allowed public
  snapshots.
- Connector-local eval suites that check behavior without central proof
  promotion.

## Out Of Scope

- Login, account, conversations, private messages, or private profile data.
- Posting, replying, liking, editing, or any write route.
- Attachments and downloads.
- Hidden APIs or routes that bypass public page boundaries.
- Broad crawling or completeness claims.
- Runtime MCP service ownership; that belongs in `abyss-stack`.
- Central eval verdicts; that belongs in `aoa-evals`.

## Statistical Boundary

The root `stats/` port may derive public, reference-only measurements from the
canonical fixture pipeline. It does not own parser or entity completeness,
claim truth, conflict or freshness interpretation, answer quality, eval
verdicts, live-source coverage, connector readiness, or runtime state. Shared
measurement grammar remains with `aoa-stats`.

## Public Repo Rule

The repo may include method, code, schemas, docs, small fixtures, and small
proof reports. It must not include full raw captures, large normalized corpora,
indexes, vector databases, graph databases, or generated caches.
