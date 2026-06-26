# AOA-XDA-D-0001: Separate Second-Source Connector Proof

## Status

Accepted.

## Context

The 4PDA connector already has a claim/conflict/freshness runtime, but one
source cannot prove connector-family architecture. XDA is close enough in shape
to stress the same forum evidence semantics while still requiring a distinct
source policy, parser, and extractor.

## Decision

Create `aoa-xda-connector` as a separate public-ready repository under
`/srv/AbyssOS/connectors/aoa-xda-connector`, with duplicated local doctrine and
the same connector-family claim/report vocabulary for now.

Do not create a shared connector monorepo yet. Do not build a full XDA MCP
before the connector proof exists.

## Options Considered

- Put XDA inside `aoa-4pda-connector`: rejected because each source connector
  must remain independently publishable and grow its own data/storage route.
- Create a shared connector-family repo first: rejected because the second
  source proof should show what is actually shared before extracting doctrine.
- Create an independent XDA repo with duplicated portable doctrine: chosen
  because it proves transfer while preserving source-specific ownership.

## Consequences

- XDA owns its parser, source policy, profile, fixtures, local evals, and
  validator.
- 4PDA remains the first implementation and stays green.
- `abyss-stack` remains the future owner for `aoa-xda-connector-mcp`.
- `aoa-evals` remains proof doctrine owner; this repo owns only its local eval
  port and reports.
- Heavy generated state stays outside Git.

## Boundary Lenses

- Owner/source: this ADR is local to XDA and references 4PDA/aoa-evals/stack as
  stronger owners for their own surfaces.
- Portability/overlay: the claim vocabulary is portable; XDA heuristics and
  fixtures are local adaptation.
- Lifecycle/time: shared doctrine extraction is deferred until duplication is
  harmful or a third connector proves the common core.
