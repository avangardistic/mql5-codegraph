# MQL5 CodeGraph

MQL5 CodeGraph is an offline static-analysis library and CLI that builds an evidence-backed graph
from MetaTrader 5 `.mq5` and `.mqh` source. It treats terminal callbacks as runtime relationships,
keeps inferred edges separate from source calls, and stores a deterministic backend-neutral JSON index.

## MVP capabilities

- Tolerant tokenizer that ignores comments and string contents during structural analysis.
- Extraction of includes, classes, structs, enums, functions, methods, event handlers, and calls.
- Project and custom include-root resolution.
- MetaTrader runtime dispatch edges for standard event handlers.
- Deterministic JSON, query/context/impact commands, and GraphML export.
- Partial results with diagnostics for incomplete or unresolved code.

## Local dashboard

Build the dashboard once, then launch it against any local MQL5 repository:

```powershell
cd web
npm ci
npm run build
cd ..
mql5-codegraph serve --root C:\work\Example-MQL5
```

The dashboard provides interactive graph navigation, symbol search, context and impact traversal,
diagnostic filtering, and safe source evidence. It binds to `127.0.0.1` by default and does not upload source.

## Development

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
mql5-codegraph analyze tests/fixtures/basic_ea --output build/basic-ea.json
mql5-codegraph status build/basic-ea.json --json
```

See [architecture](docs/architecture.md), [known limitations](docs/limitations.md), and the
[dashboard guide](docs/web-dashboard.md).
