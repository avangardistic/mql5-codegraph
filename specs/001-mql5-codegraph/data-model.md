# Data Model: MQL5 CodeGraph MVP

## SourceLocation

- `file`: normalized path relative to the analyzed root
- `line`: one-based line number
- `column`: one-based column number
- `end_line`, `end_column`: optional end position

## GraphNode

- `id`: deterministic identifier derived from kind, file, qualified name, and signature
- `kind`: file, function, method, class, struct, enum, event_handler, external_function, runtime
- `name`: short display name
- `qualified_name`: scope-qualified name
- `location`: optional SourceLocation
- `attributes`: JSON-compatible metadata

Identity is stable for unchanged declarations. Same-name overloads differ by signature.

## GraphEdge

- `id`: deterministic identifier derived from source, relationship, target, and evidence location
- `source`, `target`: node identifiers
- `relationship`: defines, includes, calls, resolves_to, runtime_dispatches, may_trigger_event
- `origin`: extracted, resolved, runtime, inferred
- `confidence`: number from 0.0 to 1.0
- `location`: optional SourceLocation
- `attributes`: JSON-compatible metadata

## Diagnostic

- `code`: stable machine-readable identifier
- `severity`: info, warning, error
- `message`: human-readable explanation
- `location`: optional SourceLocation

## CodeGraph

- `schema_version`: canonical contract version
- `metadata`: analyzed root, tool version, file count, deterministic source fingerprint
- `nodes`: sorted GraphNode collection
- `edges`: sorted GraphEdge collection
- `diagnostics`: sorted Diagnostic collection

The graph transitions from `extracted` to `resolved` to `enriched`; serialization occurs only after
all stages complete.
