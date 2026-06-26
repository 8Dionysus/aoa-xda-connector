# aoa-xda-connector

`aoa-xda-connector` is a GitHub-publishable AoA connector skeleton for public
XDA forum evidence. It proves that the connector-family claim, conflict,
freshness, applicability, warning, and answer-packet runtime can transfer
beyond 4PDA.

The repo stores method, code, schemas, policy, fixtures, seed profiles, eval
suites, and install guidance. It does not store full crawls, raw corpora, large
indexes, vector stores, or graph databases.

## What This Repository Does

| Function | Surface |
| --- | --- |
| Connector identity and boundaries | `CHARTER.md`, `BOUNDARIES.md` |
| Agent route and validation | `AGENTS.md` |
| Source policy | `connector/SOURCE_POLICY.md`, `connector/manifests/route_allowlist.yaml` |
| Storage contract | `connector/STORAGE_POLICY.md`, `.env.example` |
| Repo-local state scaffold | `.connector-state/` |
| Executable skeleton | `src/aoa_xda_connector/` |
| CLI entrypoint | `aoa-xda` |
| Schemas | `connector/schemas/` |
| Public-safe fixtures | `connector/fixtures/` |
| Local eval port | `evals/PORT.yaml`, `evals/suites/` |
| Starter profile and seeds | `connector/profiles/`, `connector/seeds/` |
| Runtime contract | `docs/RUNTIME_CONTRACT.md` |
| Validation | `scripts/validate_connector.py`, `tests/` |

## Safe Quickstart

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python scripts/validate_connector.py
python -m pytest -q
aoa-xda doctor
aoa-xda materialize fixture
aoa-xda build-index --run starter-fixture
aoa-xda build-graph --run starter-fixture
aoa-xda answer "Pixel 8 Pro husky Magisk init_boot current warning after OTA" --run starter-fixture
aoa-xda eval claim-relations
aoa-xda eval answer-packets
```

The default skeleton does not crawl XDA. It materializes a tiny sanitized XDA
thread fixture for no-network proof work.

## Storage Roots

Without environment variables, generated connector state goes to ignored
repo-local storage:

```text
.connector-state/data
.connector-state/cache
.connector-state/artifacts
```

For larger local runs, route generated state outside Git:

```bash
export CONNECTOR_FAMILY_ROOT=/path/to/connector-databases
export CONNECTOR_INSTANCE_ROOT="$CONNECTOR_FAMILY_ROOT/aoa-xda-connector"
export CONNECTOR_DATA_ROOT="$CONNECTOR_INSTANCE_ROOT/data"
export CONNECTOR_CACHE_ROOT="$CONNECTOR_INSTANCE_ROOT/cache"
export CONNECTOR_ARTIFACT_ROOT="$CONNECTOR_INSTANCE_ROOT/artifacts"
```

## Starter Profile

The first bounded proof profile is `pixel-8-pro-husky`. It is fixture-first and
models an XDA-like Android device thread with:

- root method claims around `init_boot.img`
- Magisk and fastboot tool context
- firmware/build applicability
- bootloader unlock conditions
- bootloop/data-loss warning evidence
- stale/no-longer-works language after an OTA
- a current-method correction that supersedes older advice

This is not a completeness claim about XDA or Pixel 8 Pro. It is an
architectural transfer proof.

## Search Posture

The connector must not use XDA internal search as a crawler or data source.
Instead it builds local search from allowed public snapshots:

```text
public thread pages -> normalized posts -> keyword index -> claim graph
-> evidence packets -> answer packets with source URLs, post IDs, and claim IDs
```

## Current Status

Starter pipeline is offline and deterministic. It parses sanitized XDA-like
HTML fixtures, normalizes posts, builds a keyword index, builds a claim graph,
and renders answer packets with conflict, freshness, applicability, and warning
reports. Live XDA expansion is intentionally deferred until a bounded seed run
is explicitly requested.
