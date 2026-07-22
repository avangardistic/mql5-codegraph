<!--
Sync Impact Report
- Version change: template -> 1.0.0
- Added principles: MQL5 semantic fidelity; Evidence-backed graph; Deterministic CLI contracts;
  Test corpus before claims; Small composable core
- Added sections: Technical Constraints; Development Workflow
- Templates requiring updates: ✅ existing templates remain compatible
- Follow-up TODOs: none
-->
# MQL5 CodeGraph Constitution

## Core Principles

### I. MQL5 Semantic Fidelity
The indexer MUST model MQL5 as its own language and runtime. C++-like syntax MAY be reused as
an implementation aid, but event handlers, preprocessing, include resolution, overloads, and
MetaTrader runtime dispatch MUST have explicit MQL5 behavior. Unsupported constructs MUST be
reported rather than silently guessed.

### II. Evidence-Backed Graph
Every edge MUST carry its origin, confidence, and source location. Extracted, resolved, runtime,
and inferred relationships MUST remain distinguishable. The system MUST NOT present an inferred
relationship as a direct source-code call.

### III. Deterministic CLI Contracts
Core functionality MUST be available through a scriptable CLI. Machine output MUST be stable JSON;
diagnostics MUST use stderr and non-zero exit codes. Re-indexing unchanged source with the same
configuration MUST produce semantically identical output.

### IV. Test Corpus Before Claims
Parser, resolver, and graph behavior MUST be covered by focused MQL5 fixtures before a capability is
declared supported. Tests MUST include malformed/incomplete source and negative cases. Compile
success is useful evidence but MUST NOT substitute for graph assertions.

### V. Small Composable Core
The canonical graph model MUST remain independent of visualization, databases, and agent products.
Adapters for Graphify, GraphML, Neo4j, GitNexus, or MCP MUST consume the canonical model instead of
embedding backend assumptions in parsing code.

## Technical Constraints

- The initial release MUST run locally on Windows and MUST NOT require cloud services.
- Generated indexes, caches, logs, credentials, and local MetaTrader files MUST NOT be committed.
- Public schemas and CLI output MUST be versioned before incompatible changes.
- Source analysis MUST be read-only; the indexer MUST never rewrite analyzed MQL5 files.

## Development Workflow

Requirements, plan, contracts, and tasks MUST be reviewable before implementation. Tests MUST be
added alongside each parser or graph capability. A change is complete only after automated tests,
an end-to-end fixture run, and documentation of any known parser limitations.

## Governance

This constitution overrides lower-level project guidance. Amendments require a documented reason,
an impact review of specifications and contracts, and a semantic version bump. Reviews MUST verify
compliance with all MUST statements. Exceptions require an explicit entry in the implementation
plan's Complexity Tracking section and a follow-up task.

**Version**: 1.0.0 | **Ratified**: 2026-07-22 | **Last Amended**: 2026-07-22
