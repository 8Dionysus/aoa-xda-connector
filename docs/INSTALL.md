# Install

## Fresh Clone

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python scripts/validate_connector.py
python -m pytest -q
```

## No-Network Starter Proof

```bash
aoa-xda doctor
aoa-xda materialize fixture
aoa-xda build-index --run starter-fixture
aoa-xda build-graph --run starter-fixture
aoa-xda answer "Pixel 8 Pro husky Magisk init_boot current warning after OTA" --run starter-fixture
aoa-xda eval claim-relations
aoa-xda eval answer-packets
```

## External Storage

For larger local runs:

```bash
export CONNECTOR_FAMILY_ROOT=/path/to/connector-databases
export CONNECTOR_INSTANCE_ROOT="$CONNECTOR_FAMILY_ROOT/aoa-xda-connector"
export CONNECTOR_DATA_ROOT="$CONNECTOR_INSTANCE_ROOT/data"
export CONNECTOR_CACHE_ROOT="$CONNECTOR_INSTANCE_ROOT/cache"
export CONNECTOR_ARTIFACT_ROOT="$CONNECTOR_INSTANCE_ROOT/artifacts"
```

Do not commit generated state from those roots.
