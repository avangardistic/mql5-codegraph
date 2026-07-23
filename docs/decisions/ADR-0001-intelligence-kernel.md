# ADR-0001: Intelligence Kernel before stable MCP contract

- Status: Accepted
- Date: 2026-07-22
- Owners: Project maintainers

## Context

MQL5 CodeGraph already exposes graph, query, context, impact, diagnostics, and source operations through
CLI and a local HTTP API. Planned capabilities add structural guardrails, critical paths, context packs,
and MCP. If each adapter implements its own interpretation, confidence and evidence semantics will drift.

## Decision

Introduce an internal Intelligence Kernel/service boundary that owns graph queries, rule findings, path
tracing, context assembly, schema versions, and provenance. Web, CLI, and MCP remain thin adapters.

An experimental read-only MCP stdio adapter may be built to validate the service contract, but the MCP
tool surface is not declared stable until guardrail, critical-path, and context-pack contracts mature.

## Consequences

- Positive: one source of truth across human and AI interfaces.
- Positive: protocol and UI changes do not duplicate analysis logic.
- Positive: uncertainty, confidence, and evidence remain consistent.
- Cost: a deliberate internal API and schema migration are required before feature expansion.
- Risk: premature abstraction must be avoided; the service initially wraps proven graph operations only.

## Guardrails

- All derived results retain source evidence and relationship origin.
- New schema fields are versioned and have deterministic serialization tests.
- Read-only operations are separated from analysis or future mutation operations.
- No adapter may read parser internals directly when an Intelligence Kernel operation exists.
