# MCP Rollout

This repo does not own a running MCP service.

The future stack-owned service name should be:

```text
aoa-xda-connector-mcp
```

The service should live in `abyss-stack` and call this connector as a read-only
runtime dependency.

## Allowed Tools

- status
- source route
- answer
- query graph
- query hybrid

## Forbidden Tools

- crawl
- refresh-build
- reindex
- write
- download
- attach
- login
- private/account routes
- internal-search source route

The MCP layer must pass through `agent_answer`, `evidence_chain`,
`answer_report`, `conflict_report`, `freshness_report`, `applicability_report`,
`warning_report`, `network_touched=false`, and `read_only=true`.
