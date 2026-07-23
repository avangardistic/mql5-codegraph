# Quickstart Validation: Intelligence Kernel

This guide describes the acceptance run after feature 003 is implemented. Commands run from the repository root.

## Prerequisites

- Python 3.11 or newer.
- Repository installed editable or `src` available on `PYTHONPATH`.
- No cloud service, database, MetaTrader terminal, or model API key is required.

## 1. Run deterministic unit and regression suites

```powershell
python -m unittest discover -s tests
python -m compileall -q src tests
```

Expected: all legacy and Intelligence Kernel tests pass; compileall prints no error.

## 2. Build the reference canonical graph

```powershell
mql5-codegraph analyze tests/fixtures/basic_ea --output .tmp/basic-ea.graph.json --json
```

Expected: JSON reports the fixture counts and source fingerprint; analyzed source files remain unchanged.

## 3. Prove legacy compatibility

```powershell
mql5-codegraph query .tmp/basic-ea.graph.json OnTick --json
mql5-codegraph context .tmp/basic-ea.graph.json CalculateLots --depth 1 --json
mql5-codegraph impact .tmp/basic-ea.graph.json CalculateLots --depth 3 --json
```

Expected: the existing bare array/object shapes remain unchanged and impact includes `OnTick`.

## 4. Exercise normalized v1 operations

```powershell
mql5-codegraph intelligence query .tmp/basic-ea.graph.json CalculateLots --contract-version 1 --json
mql5-codegraph intelligence path .tmp/basic-ea.graph.json OnTick CalculateLots --max-depth 5 --max-paths 3 --max-expansions 10000 --contract-version 1 --json
mql5-codegraph intelligence context-package .tmp/basic-ea.graph.json CalculateLots --context-units 40 --max-depth 2 --contract-version 1 --json
```

Expected:

- Every response declares contract `1.0.0` and graph identity.
- Every relationship/path hop exposes direction, type, origin, confidence, location, and evidence state.
- Path completion distinguishes connected, not connected, and bound-limited search.
- Context package uses at most 40 `structural_record_v1` units and reports omissions.

## 5. Prove HTTP equivalence

```powershell
mql5-codegraph serve --graph .tmp/basic-ea.graph.json --root tests/fixtures/basic_ea --no-browser
```

In another shell, submit equivalent JSON requests to:

```text
POST http://127.0.0.1:8765/api/v1/intelligence/query
POST http://127.0.0.1:8765/api/v1/intelligence/path
POST http://127.0.0.1:8765/api/v1/intelligence/context-package
```

Expected: after removing transport-only client ID and snapshot revision, HTTP v1 results match CLI v1
and direct-kernel conformance vectors. Existing `/api/query`, `/api/context`, and `/api/impact` remain usable.

## 6. Verify determinism and bounds

Run the conformance test module, which repeats reference operations 100 times and changes insertion order:

```powershell
python -m unittest tests.intelligence.test_conformance
```

Expected: byte-identical normalized JSON, exact legacy projections, bounded completion truth tables,
and unchanged canonical graph serialization before/after requests.

## 7. Run the opt-in reference-scale gate

```powershell
$env:MQL5_CODEGRAPH_PERF = "1"
python tools/benchmark_intelligence.py
Remove-Item Env:MQL5_CODEGRAPH_PERF
```

Expected: the report records machine/runtime details, builds 10,000 deterministic nodes and approximately
40,000 edges, validates at least 200 responses, and reports p50/p95/max with p95 below one second.

## US1 acceptance evidence — 2026-07-23

The first independently usable slice covers normalized `query`, `context`, `impact`, and `diagnostics`
through direct Python, CLI v1, and HTTP v1. Equivalent requests produced equal normalized envelopes after
removing the HTTP-only snapshot revision. Legacy CLI and unversioned HTTP golden fixtures remained
byte-identical.

```powershell
python -m unittest tests.intelligence.test_traversal tests.intelligence.test_conformance tests.test_cli tests.test_web_api tests.test_web_state
# Ran 24 tests in 2.896s — OK

python -m unittest discover -s tests
# Ran 43 tests in 2.990s — OK

python -m compileall -q src tests
# exit 0, no output
```

Observed evidence-state support:

- Relationship origin remains exactly `extracted`, `resolved`, `runtime`, or `inferred`.
- A configured read-only evidence probe can report `stale`, `unavailable`, or `unknown` with a stable reason.
- Locationless evidence is retained with `location: null`; it is never silently treated as available.
- Without a probe, evidence is `unknown` with `probe_not_configured` when a location exists and
  `location_missing` when it does not.

Current limitation: US1 does not configure a filesystem evidence probe for CLI or HTTP adapters, so those
surfaces honestly report unknown freshness. Proving `available` requires a future protected probe or
canonical file fingerprint; stored source locations alone are not freshness evidence.

## Feature 003 final acceptance evidence — 2026-07-23

The reference fixture was rebuilt from source and exercised through frozen legacy commands and all
normalized operations named by this guide.

```powershell
mql5-codegraph analyze tests/fixtures/basic_ea --output .tmp/basic-ea.graph.json --json
# 3 files, 16 nodes, 22 edges, 5 diagnostics

mql5-codegraph query .tmp/basic-ea.graph.json OnTick --json
mql5-codegraph context .tmp/basic-ea.graph.json CalculateLots --depth 1 --json
mql5-codegraph impact .tmp/basic-ea.graph.json CalculateLots --depth 3 --json
# legacy shapes preserved; impact contains OnTick

mql5-codegraph intelligence query .tmp/basic-ea.graph.json CalculateLots --contract-version 1 --json
mql5-codegraph intelligence path .tmp/basic-ea.graph.json OnTick CalculateLots --max-depth 5 --max-paths 3 --max-expansions 10000 --contract-version 1 --json
mql5-codegraph intelligence context-package .tmp/basic-ea.graph.json CalculateLots --context-units 40 --max-depth 2 --contract-version 1 --json
# contract 1.0.0; path contains one resolved hop with source evidence
# context package uses 22/40 structural units and reports bounded search_space omission
```

The executable US3 acceptance test repeats the same normalized budget semantics through direct Python,
CLI, and real HTTP and compares the canonical envelopes after removing HTTP snapshot revision.

```powershell
python -m unittest tests.intelligence.test_models tests.intelligence.test_matching tests.intelligence.test_traversal tests.intelligence.test_paths tests.intelligence.test_context tests.intelligence.test_conformance
# Ran 48 tests in 2.395s — OK

python -m unittest tests.test_cli tests.test_web_api tests.test_web_state tests.test_indexer tests.test_lexer tests.test_parser
# Ran 26 tests in 2.050s — OK

python -m unittest discover -s tests
# Ran 74 tests in 4.402s — OK

python -m compileall -q src tests tools
# exit 0, no output

cd web
npm run lint
# exit 0
npm run build
# exit 0; production bundle generated successfully
cd ..
```

`python -m unittest discover -s tests/intelligence` is not a valid package-qualified invocation for this
suite because it loads modules as top-level files and breaks their relative helper imports. The explicit
`tests.intelligence.*` command above and root `discover -s tests` are the supported gates.

## Cleanup

Remove only the generated `.tmp/basic-ea.graph.json` after validating its resolved path is inside this repository.
