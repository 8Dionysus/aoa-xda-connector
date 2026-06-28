# AGENTS.md

## Applies to

This card applies to `aoa-xda-connector/kag/` and every nested path until a
nearer card narrows the lane.

## Role

`kag/` is the local KAG provider home for `aoa-xda-connector`.

It exposes compact source-linked records over the XDA connector policy, storage
boundary, and runtime contract surfaces for `aoa-kag` registry, composition,
and MCP consumers.

## Read before editing

Read the root `AGENTS.md`, `README.md`, `BOUNDARIES.md`,
`connector/README.md`, `connector/SOURCE_POLICY.md`,
`connector/STORAGE_POLICY.md`, `docs/RUNTIME_CONTRACT.md`, and
`kag/manifest.json` before changing provider records.

## Boundaries

Keep XDA connector meaning with this repository's source surfaces. Keep shared
KAG schema, registry, composition, and provider validation with `aoa-kag`.
Keep runtime serving with `abyss-stack`. Keep raw captures, generated corpora,
indexes, graph artifacts, vectors, caches, and full exports outside Git in the
storage roots named by the connector.

## Validation

Use the owner validator named in `manifest.json`, then validate this provider
through the `aoa-kag` local subtree validator.

## Closeout

Report provider records changed, source-return route changed, owner validation,
`aoa-kag` validation, and the next MCP consumer route.
