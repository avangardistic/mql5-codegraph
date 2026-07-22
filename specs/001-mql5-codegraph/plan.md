# Implementation Plan: MQL5 CodeGraph MVP

**Branch**: `main` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

## Summary

Build an offline-first Python library and CLI that performs tolerant MQL5 lexical and structural
analysis, resolves project includes and calls, enriches the graph with MetaTrader runtime events,
and exposes deterministic JSON plus GraphML export.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Python standard library for MVP; optional integrations added behind adapters

**Storage**: Versioned canonical JSON files

**Testing**: `unittest` with unit, integration, and CLI tests

**Target Platform**: Windows first; portable to Linux/macOS for static analysis

**Project Type**: Library and CLI static-analysis tool

**Performance Goals**: Index 10,000 lines in under 5 seconds; query 10,000 nodes in under 2 seconds

**Constraints**: Offline, read-only source analysis, deterministic output, tolerant of incomplete source

**Scale/Scope**: Single repositories up to 100,000 source lines for the MVP

## Constitution Check

- MQL5 semantic fidelity: PASS; dedicated tokenizer, parser, resolver, and runtime enrichment stages.
- Evidence-backed graph: PASS; all edges contain origin, confidence, and optional source span.
- Deterministic CLI contracts: PASS; sorted canonical JSON and structured command output.
- Test corpus before claims: PASS; fixtures and assertions precede capability completion.
- Small composable core: PASS; graph model has no visualization or database dependency.

Post-design check: PASS. No constitutional exceptions are required.

## Project Structure

```text
src/mql5_codegraph/
├── cli.py
├── diagnostics.py
├── graph.py
├── indexer.py
├── lexer.py
├── parser.py
├── resolver.py
├── runtime.py
└── exporters/
    └── graphml.py

tests/
├── fixtures/basic_ea/
├── test_cli.py
├── test_indexer.py
├── test_lexer.py
└── test_parser.py
```

**Structure Decision**: A single Python distribution keeps the canonical model and analysis stages
separate by module. Exporters depend inward on the graph model; the core never imports exporters.

## Complexity Tracking

No constitution violations or exceptional complexity are planned.
