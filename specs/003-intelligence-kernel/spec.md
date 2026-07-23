# Feature Specification: Intelligence Kernel

**Feature Branch**: `main`

**Created**: 2026-07-22

**Status**: Implemented

**Input**: Establish one evidence-backed intelligence boundary for graph queries, path tracing, impact analysis, and bounded AI context so CLI, web, exports, and future MCP capabilities cannot develop conflicting semantics.

## User Scenarios & Testing

### User Story 1 - Receive consistent intelligence everywhere (Priority: P1)

As an MQL5 maintainer, I receive the same graph interpretation for the same request regardless of
whether I use the command line, local dashboard, or a future agent-facing interface.

**Why this priority**: A single interpretation is the foundation required before adding MCP,
structural guardrails, context augmentation, or critical-path visualization.

**Independent Test**: Run equivalent symbol-query, context, and impact requests through two supported
interfaces and verify that their normalized results, evidence, ordering, and truncation metadata agree.

**Acceptance Scenarios**:

1. **Given** the same canonical graph and request, **When** two interfaces request symbol context,
   **Then** they receive semantically equivalent nodes, relationships, evidence, and limits.
2. **Given** unchanged graph data and request parameters, **When** an operation is repeated,
   **Then** the normalized result and ordering remain deterministic.
3. **Given** an unsupported or invalid request, **When** any interface submits it, **Then** the same
   stable error category and actionable explanation are returned without exposing parser internals.

---

### User Story 2 - Trace relationships with inspectable evidence (Priority: P2)

As a developer assessing unfamiliar MQL5 code, I can trace how one symbol reaches another and
understand whether every step was extracted, resolved, runtime-derived, or inferred.

**Why this priority**: A path without provenance can mislead both humans and AI, especially around
MetaTrader runtime dispatch and ambiguous symbol resolution.

**Independent Test**: Trace a known path from an event handler to a downstream function and verify
that every hop includes direction, relationship type, confidence, origin, and source evidence.

**Acceptance Scenarios**:

1. **Given** two connected symbols, **When** a directed path is requested, **Then** the result contains
   an ordered sequence of nodes and relationships with evidence for every hop.
2. **Given** multiple valid paths, **When** bounded alternatives are requested, **Then** results use a
   documented deterministic ranking and report whether additional paths were omitted.
3. **Given** no valid path within the requested direction or limits, **When** tracing completes,
   **Then** the result distinguishes “not connected” from “search limit reached.”
4. **Given** an inferred or runtime-derived relationship, **When** it appears in a result,
   **Then** it is visibly distinguishable from a direct source-code relationship.

---

### User Story 3 - Assemble bounded context for AI review (Priority: P3)

As an AI-assisted MQL5 developer, I can request a compact context package around a task or symbol
that preserves the most relevant code relationships, diagnostics, and evidence without flooding the
model with the entire repository.

**Why this priority**: Bounded, reproducible context is the first practical step toward reducing AI
blind spots while keeping prompt generation and model-provider concerns outside the core.

**Independent Test**: Request context for a known symbol under a fixed budget and verify that the
same ranked evidence is returned, the budget is respected, and omissions are disclosed.

**Acceptance Scenarios**:

1. **Given** a symbol and a context budget, **When** context is assembled, **Then** the result prioritizes
   direct evidence, relevant relationships, diagnostics, and source locations without exceeding the budget.
2. **Given** ambiguous symbol matches, **When** context is requested, **Then** alternatives and their
   confidence are retained instead of silently selecting one interpretation.
3. **Given** more relevant material than the budget permits, **When** the package is returned,
   **Then** it declares truncation and summarizes what categories were omitted.

### Edge Cases

- The canonical graph is empty, uses an unsupported schema version, or is missing optional metadata.
- A request identifies no symbol, one symbol, or several equally plausible symbols.
- Paths contain cycles, runtime dispatch edges, unresolved external nodes, or inferred relationships.
- Source files have changed or disappeared since indexing, making stored evidence stale.
- A depth, result-count, path-count, or context budget is zero, negative, or above the supported maximum.
- Equivalent adapters encode optional values differently or request operations in different orders.
- A large graph would exceed time or result limits before traversal completes.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST provide one authoritative intelligence boundary for graph query,
  neighborhood context, upstream impact, directed path tracing, diagnostics, and bounded context assembly.
- **FR-002**: Existing and future user interfaces MUST consume authoritative operations rather than
  independently interpreting canonical graph relationships.
- **FR-003**: Equivalent requests against the same graph version MUST produce semantically equivalent,
  deterministically ordered results across interfaces.
- **FR-004**: Every relationship-based result MUST preserve relationship direction, type, origin,
  confidence, and available source location.
- **FR-005**: The system MUST distinguish extracted, resolved, runtime-derived, and inferred evidence
  in all user-visible intelligence results.
- **FR-006**: Traversal operations MUST accept explicit bounds for depth and result count, and path
  operations MUST additionally bound path count or search effort.
- **FR-007**: Every bounded result MUST disclose applied limits, truncation status, and whether the
  search completed within those limits.
- **FR-008**: Path tracing MUST distinguish no directed connection from an incomplete bounded search.
- **FR-009**: Ambiguous symbol matches and unresolved relationships MUST remain visible and MUST NOT be
  converted into false certainty.
- **FR-010**: Context assembly MUST rank and select relevant graph evidence reproducibly under a declared budget.
- **FR-011**: Context results MUST identify included evidence and summarize categories omitted because of bounds.
- **FR-012**: Intelligence requests and results MUST declare compatible schema versions, with stable
  errors for unsupported versions or invalid parameters.
- **FR-013**: Read-only intelligence operations MUST NOT modify analyzed MQL5 source files or the canonical graph.
- **FR-014**: Existing CLI and dashboard behavior MUST remain compatible unless an explicitly versioned
  contract documents a change.
- **FR-015**: Automated conformance tests MUST verify deterministic results, cross-interface equivalence,
  evidence preservation, bounded traversal, ambiguity handling, and negative cases.
- **FR-016**: Export adapters MAY consume the canonical graph directly when they only transform its
  representation and do not reinterpret analysis semantics.

### Key Entities

- **Intelligence Request**: A read-only operation, target symbols, graph version, direction, filters,
  and explicit traversal or context bounds.
- **Intelligence Result**: Deterministically ordered data, schema version, graph identity, applied
  limits, completion state, truncation details, and stable diagnostics.
- **Evidence Reference**: A relationship or diagnostic's origin, confidence, source location, and
  stale-or-unavailable evidence state.
- **Directed Path**: An ordered node-and-relationship sequence plus ranking and completion metadata.
- **Context Package**: A bounded, ranked collection of symbols, relationships, diagnostics, and
  evidence suitable for downstream human or AI consumption.

## Success Criteria

### Measurable Outcomes

- **SC-001**: One hundred percent of conformance cases for equivalent CLI and dashboard operations
  return semantically equivalent normalized results.
- **SC-002**: One hundred percent of relationship hops returned by context, impact, or path operations
  expose direction, type, origin, confidence, and an evidence state.
- **SC-003**: Repeating each reference request 100 times against an unchanged graph produces identical
  normalized output and ordering.
- **SC-004**: All bounded-operation tests stay within their declared depth, item, path, and context limits
  and accurately report every tested truncation condition.
- **SC-005**: On the reference 10,000-node graph, at least 95 percent of bounded intelligence requests
  complete in under one second on the documented test machine.
- **SC-006**: All existing CLI, web API, indexer, and graph regression tests continue to pass.
- **SC-007**: A maintainer can identify why each hop in a returned path exists and where its evidence
  originated without inspecting parser implementation code.

## Assumptions

- The canonical `CodeGraph` remains the backend-neutral source of graph data and deterministic serialization.
- This feature establishes the internal intelligence contract; a stable public MCP tool surface is deferred.
- Structural rule definitions, prompt templates, model-provider integration, and critical-path visualization
  are separate features that will consume this boundary.
- The first context budget may be expressed as deterministic structural units rather than model-specific tokens.
- Analysis remains local, single-user, read-only, and compatible with persisted graphs produced by the current release.
