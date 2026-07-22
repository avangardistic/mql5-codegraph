# Implementation Plan: Local Web Dashboard

**Branch**: `main` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

## Summary

Add a loopback-only threaded Python server and versioned HTTP API over the canonical CodeGraph, then
build a responsive React/Cytoscape dashboard compiled into package-owned static assets and launched by
the existing CLI.

## Technical Context

**Language/Version**: Python 3.11+, TypeScript 5.9, React 19

**Primary Dependencies**: Python standard library; React, Vite, Cytoscape, Lucide React for the frontend

**Storage**: In-memory graph snapshot; existing deterministic JSON remains optional persistence

**Testing**: `unittest`, Node build/typecheck, HTTP integration tests, local browser smoke verification

**Target Platform**: Windows-first loopback web application

**Project Type**: Python CLI/library plus static web frontend

**Performance Goals**: UI projection capped at 2,000 nodes; API query p95 below 250 ms on 10,000 nodes

**Constraints**: No cloud upload, same-origin API, safe source containment, one analysis job at a time

**Scale/Scope**: Local repositories up to existing indexer limits; browser projection independently bounded

## Constitution Check

- MQL5 semantic fidelity: PASS; dashboard consumes the canonical engine without reinterpreting source.
- Evidence-backed graph: PASS; edge origin, confidence, and location remain visible.
- Deterministic CLI contracts: PASS; `serve` extends CLI and API responses have stable contracts.
- Test corpus before claims: PASS; API and UI use the existing fixture plus real repository smoke test.
- Small composable core: PASS; web/API modules depend on CodeGraph, never the reverse.

Post-design check: PASS. Local-only serving is required to preserve source privacy and filesystem access.

## Project Structure

```text
src/mql5_codegraph/web/
├── api.py
├── server.py
└── state.py

src/mql5_codegraph/web_static/       # production frontend build copied here

web/
├── src/
│   ├── components/
│   ├── api.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── styles.css
├── index.html
├── package.json
└── vite.config.ts

tests/
├── test_web_api.py
└── test_web_state.py
```

**Structure Decision**: The Python package owns runtime state and API. `web/` owns authored frontend
source; its deterministic build is copied into package data for `mql5-codegraph serve`.

## Complexity Tracking

No constitution violations. React is isolated to the visualization surface and does not enter core analysis.
