# AGENTS.md

Root route card for `aoa-xda-connector`.

## Purpose

`aoa-xda-connector` is an AoA external-source connector skeleton for building
local, policy-gated search, graph, and claim evidence from public XDA forum
thread/post pages, plus bounded owner-local statistics over that evidence.

The repository is GitHub-publishable method and code. It is not a corpus dump.

## Owner Lane

This repository owns:

- XDA source policy and route allowlist/denylist
- XDA public thread parser, normalizer, claim extractor, index, graph, answer
  packet, and local eval skeletons
- small synthetic fixtures and bounded starter profile routes
- owner-local statistical questions over normalized XDA and claim-graph
  evidence
- connector-local validation and install route docs

It does not own:

- XDA content or platform policy
- login, account, private messages, write, reply, attachment, or download
  routes
- broad crawler operation or live corpus expansion
- full raw captures, large indexes, graph databases, embeddings, or caches
- runtime/MCP deployment, which belongs in `abyss-stack`
- central eval verdicts or proof doctrine, which belong in `aoa-evals`
- shared statistical grammar or cross-owner composition, which belong in
  `aoa-stats`

## Start Here

1. `README.md`
2. `CHARTER.md`
3. `BOUNDARIES.md`
4. `connector/SOURCE_POLICY.md`
5. `connector/STORAGE_POLICY.md`
6. `docs/ARCHITECTURE.md`
7. `docs/RUNTIME_CONTRACT.md`
8. `docs/AGENT_INSTALL_ROUTE.md`
9. `docs/decisions/README.md`
10. `stats/README.md` for owner-local statistical questions

Before large data, runtime, AI, or benchmark work, also read
`/etc/abyss-machine/AGENTS.md` and `/etc/abyss-machine/storage-policy.json`.

## Boundaries

- Do not run broad crawls unless the operator explicitly asks for a bounded
  public crawl.
- Do not use XDA internal search as a crawler or corpus source.
- Do build local deep search over allowed public snapshots.
- Do not download attachments.
- Do not use login/account/private/conversation/write/reply routes.
- Do not commit raw captures, indexes, graph DBs, vector stores, caches, or full
  exports.
- The repo-local `.connector-state/` directory is an ignored workspace for
  small starter runs. Treat generated files inside it as local state, not source
  truth.

## Validation

Run from the repository root:

```bash
python scripts/validate_connector.py
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m aoa_xda_connector.cli doctor
PYTHONPATH=src python -m aoa_xda_connector.cli materialize fixture
PYTHONPATH=src python -m aoa_xda_connector.cli build-index --run starter-fixture
PYTHONPATH=src python -m aoa_xda_connector.cli build-graph --run starter-fixture
PYTHONPATH=src python -m aoa_xda_connector.cli eval claim-relations
PYTHONPATH=src python -m aoa_xda_connector.cli eval answer-packets
python /srv/AbyssOS/aoa-evals/scripts/validate_local_eval_port.py --target-root . --json
AOA_STATS_ROOT=/path/to/aoa-stats python scripts/validate_local_stats_port.py
```

The CI workflow owns the exhaustive repository route. Ordinary Markdown
explains behavior and links to executable owners rather than duplicating
command catalogs.

## Closeout

Report changed surfaces, validation results, skipped live crawl or storage
checks, and the next safe step. The first safe materialized step is
`aoa-xda materialize fixture`; any live XDA expansion must start from explicit
bounded public seeds and keep generated data outside Git.
