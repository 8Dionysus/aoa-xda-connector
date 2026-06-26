# Connector-Family Claim Contract

This document is duplicated locally while the connector family is still small.
It should stay vocabulary-compatible with other connector repos.

## Claim

A claim is a source-grounded assertion extracted from a public post. It can be
a method, warning, status, context, or risk claim.

Every claim needs:

- stable `claim_id`
- `claim_kind`
- action label
- target/tool/context labels when available
- source post reference
- evidence span
- freshness context
- confidence basis

## Claim Relation

Contract key: `claim_relation`.

Claim relations make forum information usable as a changing knowledge base:

- source supports or warns about a claim
- a method uses a tool
- a method targets an object
- a method requires a condition
- a warning targets an object or action
- a later claim supersedes an older claim
- claims contradict or contextualize each other

## Reports

The answer packet carries four portable report families:

- `conflict_report`
- `freshness_report`
- `applicability_report`
- `warning_report`

These reports are not decorative. They are how the agent avoids treating old,
risky, context-limited, or disputed forum advice as timeless truth.

## Insufficient Evidence

`insufficient_evidence` is a first-class successful state. It means local
evidence cannot safely support an answer.

## Source-Specific Boundary

Parsers, route policies, fixture choices, source URL shapes, quote removal, and
extractor heuristics remain source-specific. Claim/report vocabulary is the
portable part.
