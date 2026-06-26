# Storage Policy

Git stores method, code, schemas, small fixtures, eval suites, docs, and small
proof reports.

Git must not store:

- full raw captures
- large normalized corpora
- indexes
- vectors
- graph databases
- SQLite databases
- caches
- full exports

## Environment Roots

Use these portable variables for generated state:

```text
CONNECTOR_FAMILY_ROOT
CONNECTOR_INSTANCE_ROOT
CONNECTOR_DATA_ROOT
CONNECTOR_CACHE_ROOT
CONNECTOR_ARTIFACT_ROOT
```

If the specific roots are unset, the connector uses ignored repo-local default
state under `.connector-state/` for tiny fixture runs.

Host-specific examples such as
`/srv/abyss-machine/storage/connectors/aoa-xda-connector` are runtime examples,
not public repo assumptions.
