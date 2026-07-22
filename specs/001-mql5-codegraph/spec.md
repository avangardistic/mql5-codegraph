# Feature Specification: MQL5 CodeGraph MVP

**Feature Branch**: `main`

**Created**: 2026-07-22

**Status**: Approved for MVP implementation

**Input**: Build a dedicated, well-structured repository on drive D that indexes and diagrams MQL5 code.

## User Scenarios & Testing

### User Story 1 - Index an MQL5 repository (Priority: P1)

As an MQL5 developer, I can analyze a folder containing `.mq5` and `.mqh` files and receive a
canonical graph of files, symbols, includes, definitions, calls, and runtime event handlers.

**Why this priority**: All visualization and agent integrations depend on trustworthy extraction.

**Independent Test**: Analyze the supplied fixture and inspect the generated JSON without any
external database or cloud service.

**Acceptance Scenarios**:

1. **Given** a valid EA with an included class, **When** analysis runs, **Then** files, functions,
   classes, methods, include links, definitions, and resolvable calls appear in the graph.
2. **Given** an `OnTick` handler, **When** analysis runs, **Then** a runtime dispatch edge from the
   MetaTrader terminal appears and is not mislabeled as a source-code call.
3. **Given** incomplete MQL5 source, **When** analysis runs, **Then** partial results and diagnostics
   are returned without modifying the source.

---

### User Story 2 - Explore and assess impact (Priority: P2)

As a coding agent or developer, I can query symbols, inspect their neighborhood, and estimate the
upstream impact of changing a symbol.

**Why this priority**: A graph becomes useful for maintenance only when it can answer targeted
questions without loading the entire repository.

**Independent Test**: Run query, context, and impact commands against a saved fixture index.

**Acceptance Scenarios**:

1. **Given** a saved graph, **When** a user queries a symbol name, **Then** matching nodes and
   source locations are returned as JSON.
2. **Given** a called function, **When** upstream impact is requested, **Then** callers are returned
   by bounded graph traversal with their distance from the target.

---

### User Story 3 - Export to graph tools (Priority: P3)

As a tool integrator, I can export the canonical graph in interoperable formats without changing
the parser or resolver.

**Why this priority**: It enables later Graphify, GraphML, Neo4j, and MCP integration while keeping
the core independent.

**Independent Test**: Export a saved index and validate that all node and edge identifiers remain
stable across the canonical JSON and GraphML representations.

**Acceptance Scenarios**:

1. **Given** a canonical graph, **When** GraphML export runs, **Then** a valid directed graph file is
   produced with node kinds and edge relationship types.

### Edge Cases

- Include targets may be local, absent, angle-bracket standard-library paths, or duplicated.
- Functions may be overloaded, qualified, declared without bodies, or nested in classes.
- Comments and strings may contain braces, parentheses, or text resembling calls.
- Source may contain macros, conditional compilation, Unicode, or unmatched braces.
- Multiple files may declare symbols with the same short name.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST discover `.mq5` and `.mqh` files recursively with configurable exclusions.
- **FR-002**: The system MUST tokenize source without treating comments or strings as executable code.
- **FR-003**: The system MUST extract includes, classes, structs, enums, functions, methods, event
  handlers, and function calls with source locations.
- **FR-004**: The system MUST resolve local includes using the source directory, project root, and
  user-supplied include roots.
- **FR-005**: The system MUST build a directed canonical graph whose edges include evidence and confidence.
- **FR-006**: The system MUST distinguish extracted, resolved, runtime, and inferred relationships.
- **FR-007**: The system MUST save and load a versioned JSON index deterministically.
- **FR-008**: Users MUST be able to run analyze, status, query, context, impact, and export commands.
- **FR-009**: The system MUST emit diagnostics for unresolved includes, unresolved calls, and parse recovery.
- **FR-010**: The system MUST never modify analyzed MQL5 source.
- **FR-011**: The MVP MUST export GraphML through an adapter over the canonical graph.
- **FR-012**: Automated tests MUST cover extraction, resolution, runtime events, traversal, and CLI behavior.

### Key Entities

- **SourceFile**: An analyzed MQL5 file with normalized repository-relative identity.
- **Symbol**: A declaration such as a function, method, type, variable, or event handler.
- **Relationship**: A directed, typed connection with evidence, confidence, and source location.
- **Diagnostic**: A non-fatal or fatal analysis observation tied to a source location when possible.
- **CodeGraph**: The versioned aggregate containing metadata, nodes, edges, and diagnostics.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The reference fixture is indexed end-to-end with all asserted symbols and relationships present.
- **SC-002**: Repeated analysis of unchanged input produces byte-identical canonical JSON.
- **SC-003**: Malformed fixture analysis completes without source mutation and reports at least one diagnostic.
- **SC-004**: Query, context, and impact operations complete in under two seconds for a 10,000-node saved graph on a development workstation.
- **SC-005**: All automated tests pass on Windows with a supported Python version.

## Assumptions

- The MVP performs tolerant static analysis; it is not a replacement for MetaEditor compilation.
- Exact macro expansion and full overload/type inference are incremental post-MVP capabilities.
- Local JSON is the source of truth; databases and hosted services are out of scope for the MVP.
- Graphify and GitNexus adapters beyond GraphML are planned extensions, not MVP acceptance gates.
