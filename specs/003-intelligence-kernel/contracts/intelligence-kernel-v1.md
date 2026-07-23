# Intelligence Kernel Contract v1

**Contract version**: `1.0.0`

This contract is normative for direct library calls and normalized adapter surfaces. Canonical JSON uses
UTF-8, sorted object keys, compact or indented whitespace without semantic difference, and the ordering
defined below. Unknown major versions are rejected. A newer minor version may add optional fields only.

## Operations

| Operation | Targets | Defaults | Primary output |
| --- | --- | --- | --- |
| `query` | One text selector | `max_items=30` | Ordered matches |
| `context` | One selector | `direction=both`, `max_depth=1`, `max_items=900` | Bounded neighborhood |
| `impact` | One selector | `direction=incoming`, `max_depth=3`, `max_items=2000` | Upstream entries and evidence paths |
| `diagnostics` | None or filters | `max_items=250` | Filtered diagnostics and counts |
| `path` | Source and target | `direction=outgoing`, `max_depth=5`, `max_paths=3`, `max_expansions=10000` | Directed alternatives |
| `context_package` | One selector | `direction=both`, `max_depth=2`, `context_units=100` | Ranked structural context |

All operations validate irrelevant fields, graph schema, contract major, bounds, and optional expected
fingerprint before traversal. Operations do not mutate graph objects or source files.

## Normalized envelope

```json
{
  "contract_version": "1.0.0",
  "operation": "path",
  "graph_identity": {
    "graph_schema_version": "1.0.0",
    "source_fingerprint": "sha256-like-project-fingerprint",
    "snapshot_revision": 1
  },
  "request": {},
  "resolution": [],
  "nodes": [],
  "relationships": [],
  "paths": [],
  "context_package": null,
  "diagnostics": [],
  "limits_applied": {},
  "completion": {
    "search_complete": true,
    "truncated": false,
    "reason": "complete",
    "omitted_counts": {},
    "explored_nodes": 0,
    "explored_edges": 0
  }
}
```

Absent operation-specific data uses empty arrays or null; fields are not omitted.

## Deterministic ordering

- Matches: match rank, qualified-name case-fold, kind, node ID.
- Traversal nodes: distance, kind, qualified-name case-fold, node ID.
- Relationships: distance, origin penalty, relationship, source ID, target ID, edge ID.
- Diagnostics: severity (`error`, `warning`, `info`), code, file, line, column, message.
- Paths: `evidence_first_v1` ranking from `research.md`, then edge-ID sequence.
- Context items: tier, distance, origin penalty, negative confidence basis points, subject ID.

Implementations must never rely on set/dictionary insertion order. Confidence participates in ordering as
integer basis points; float formatting never contributes to IDs.

## Evidence requirements

Every returned relationship, diagnostic, and path hop includes one `EvidenceReference`. `origin` retains
the canonical distinction between extracted, resolved, runtime, and inferred. A runtime edge is never
reported as a direct source-code call. When no evidence probe is supplied, location freshness is `unknown`.

## Bounds and completion

Search work and returned output are separately bounded. The first deterministic bound that prevents
completion becomes `completion.reason`. `not_connected` may be returned only after eligible directed
search is exhausted. A max-depth or max-expansion stop is not evidence of disconnection.

Context packing is atomic: a relationship is never emitted without both endpoints. Omission counts are
reported by category; null means omission is known but exact counting would violate a search bound.

## Error envelope

```json
{
  "error": {
    "contract_version": "1.0.0",
    "category": "request",
    "code": "invalid_parameter",
    "message": "bounds.max_depth must be between 0 and 5",
    "field": "bounds.max_depth",
    "retryable": false
  }
}
```

Adapters may map status/exit codes but must preserve normalized `code` semantics. Parser exceptions,
filesystem paths outside approved evidence, and stack details never cross this boundary.

## Compatibility policy

- Patch: bug fix with identical valid shapes and semantics.
- Minor: additive optional fields or operation values that old clients can ignore.
- Major: removed/renamed fields, changed defaults/ranking/error semantics, or incompatible operation behavior.
- New major HTTP contracts use a new `/api/vN` path; CLI requires the requested contract major.
