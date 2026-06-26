# Runtime Contract

The XDA connector runtime is read-only and no-network by default.

## Answer Packet

Answer packets must preserve:

- source URLs
- post IDs
- claim IDs
- evidence_chain
- agent_answer
- `conflict_report`
- `freshness_report`
- `applicability_report`
- `warning_report`
- `network_touched=false`
- `read_only=true`

## Report Semantics

`conflict_report` explains whether primary evidence has supporting,
conflicting, superseding, or contextual evidence.

`freshness_report` explains whether the local evidence appears current,
possibly superseded, conflicting, or insufficient.

`applicability_report` explains device, firmware, build, tool, and condition
context.

`warning_report` separates risk evidence from ordinary method advice.

`insufficient_evidence` means the connector refused to answer beyond its local
evidence. This is a valid output, not a failure.

## Future MCP Handoff

`abyss-stack` may later host `aoa-xda-connector-mcp`.

Allowed MCP tools should be thin read-only wrappers:

- status
- source route
- answer
- query graph
- query hybrid

Forbidden MCP tools:

- crawl
- refresh-build
- reindex
- write
- download
- attach
- login
- private/account routes
- internal-search source route

The MCP wrapper must not own parser, crawler, graph, or answer logic.
