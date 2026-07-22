# Quickstart Validation

## Prerequisites

- Python 3.11 or newer
- PowerShell

## Install for development

```powershell
python -m pip install -e .
```

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## Analyze the fixture

```powershell
mql5-codegraph analyze tests/fixtures/basic_ea --output build/basic-ea.json
mql5-codegraph status build/basic-ea.json --json
mql5-codegraph query build/basic-ea.json OnTick --json
mql5-codegraph impact build/basic-ea.json CalculateLots --json
mql5-codegraph export build/basic-ea.json --format graphml --output build/basic-ea.graphml
```

Expected outcome: commands succeed, `OnTick` has a `runtime_dispatches` incoming edge, the helper
method is connected to its caller, and GraphML contains the same canonical node identifiers.
