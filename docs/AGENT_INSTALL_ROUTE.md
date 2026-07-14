# Agent Install Route

An agent installing this connector should:

1. Read `AGENTS.md`, `BOUNDARIES.md`, `connector/SOURCE_POLICY.md`, and
   `connector/STORAGE_POLICY.md`.
2. Follow the bounded operator route in the root `AGENTS.md`; the package
   metadata, CLI parser, validator, tests, and CI workflow remain the
   executable owners.
3. Confirm the no-network starter proof before considering connected data.
4. Configure external storage roots before any bounded public source run.

The agent must not perform live XDA network expansion unless explicitly asked
and given bounded public seed scope.
