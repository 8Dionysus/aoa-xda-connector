# Agent Install Route

An agent installing this connector should:

1. Read `AGENTS.md`, `BOUNDARIES.md`, `connector/SOURCE_POLICY.md`, and
   `connector/STORAGE_POLICY.md`.
2. Create a Python environment and install the repo in editable mode.
3. Run `python scripts/validate_connector.py`.
4. Run `PYTHONPATH=src python -m pytest -q`.
5. Run `PYTHONPATH=src python -m aoa_xda_connector.cli doctor`.
6. Run the no-network starter proof:

```bash
PYTHONPATH=src python -m aoa_xda_connector.cli materialize fixture
PYTHONPATH=src python -m aoa_xda_connector.cli build-index --run starter-fixture
PYTHONPATH=src python -m aoa_xda_connector.cli build-graph --run starter-fixture
PYTHONPATH=src python -m aoa_xda_connector.cli eval claim-relations
PYTHONPATH=src python -m aoa_xda_connector.cli eval answer-packets
```

The agent must not perform live XDA network expansion unless explicitly asked
and given bounded public seed scope.
