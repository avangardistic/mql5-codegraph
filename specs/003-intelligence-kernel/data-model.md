# Data Model: Intelligence Kernel v1

## Version and identity

### ContractVersion

- **Value**: semantic version string, initially `1.0.0`.
- **Validation**: major version must be supported; unknown required fields or incompatible major versions fail.
- **Rule**: contract version is independent of canonical graph schema and package version.

### GraphIdentity

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `graph_schema_version` | string | yes | Copied from `CodeGraph.schema_version` |
| `source_fingerprint` | string or null | yes | Stable repository/configuration identity when available |
| `snapshot_revision` | integer or null | yes | Process-local informational revision; non-negative |

An optional request fingerprint must match `source_fingerprint` or the operation fails with
`graph_identity_mismatch`.

## Requests

### IntelligenceRequest

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `contract_version` | string | yes | Supported major version |
| `operation` | enum | yes | `query`, `context`, `impact`, `diagnostics`, `path`, `context_package` |
| `targets` | ordered SymbolSelector array | operation-specific | One for context/impact/context package; two for path |
| `direction` | enum | no | `incoming`, `outgoing`, `both`; default depends on operation |
| `relationship_types` | sorted string array | no | Empty means operation policy default |
| `node_kinds` | sorted string array | no | Empty means all kinds |
| `bounds` | IntelligenceBounds | yes | Canonical explicit bounds |
| `expected_source_fingerprint` | string or null | no | Stale-work guard |
| `client_request_id` | string or null | no | Echo only; excluded from semantic equality/cache keys |

Contradictory or irrelevant fields are rejected instead of ignored.

### SymbolSelector

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `value` | string | yes | Non-empty ID, qualified name, short name, or substring |
| `kind` | string or null | no | Optional exact node-kind filter |

### IntelligenceBounds

| Field | Range | Default purpose |
| --- | --- | --- |
| `max_depth` | 0..5 | Traversal depth; zero returns targets only |
| `max_items` | 1..2000 | Maximum emitted primary items |
| `max_paths` | 1..20 | Maximum emitted path alternatives |
| `max_expansions` | 1..100000 | Maximum search work |
| `context_units` | 1..10000 | `structural_record_v1` package budget |

Defaults are defined per operation in the v1 contract. Legacy projectors supply their historical defaults.

## Resolution and evidence

### TargetResolution

| Field | Type | Meaning |
| --- | --- | --- |
| `selector` | SymbolSelector | Original normalized selector |
| `status` | enum | `matched`, `ambiguous`, `no_match` |
| `candidates` | Candidate array | All equally ranked top candidates before output bounds |
| `omitted_candidates` | integer or null | Exact count when cheaply known |

Candidate ordering is exact ID, exact qualified name, exact short name, substring; then qualified-name
case-fold, kind, and node ID. Ambiguity is data, not an exception.

### EvidenceReference

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `subject_id` | string | yes | Edge or diagnostic stable ID |
| `origin` | enum | yes | `extracted`, `resolved`, `runtime`, `inferred` |
| `confidence` | number | yes | Inclusive 0.0..1.0 |
| `location` | SourceLocation or null | yes | Canonical graph location |
| `state` | enum | yes | `available`, `stale`, `unavailable`, `unknown`, `not_applicable` |
| `state_reason` | string or null | yes | Stable reason such as `source_changed` or `location_missing` |

Every returned relationship and path hop has exactly one evidence reference. Missing location never
implicitly means stale or unavailable.

## Results

### IntelligenceResult

| Field | Type | Required |
| --- | --- | --- |
| `contract_version` | string | yes |
| `operation` | enum | yes |
| `graph_identity` | GraphIdentity | yes |
| `request` | normalized IntelligenceRequest | yes |
| `resolution` | TargetResolution array | yes |
| `nodes` | canonical node summary array | yes |
| `relationships` | relationship-with-evidence array | yes |
| `paths` | DirectedPath array | yes |
| `context_package` | ContextPackage or null | yes |
| `diagnostics` | diagnostic-with-evidence array | yes |
| `limits_applied` | IntelligenceBounds | yes |
| `completion` | Completion | yes |

All arrays are present, even when empty, and use contract-defined deterministic ordering.

### Completion

| Field | Type | Meaning |
| --- | --- | --- |
| `search_complete` | boolean | Eligible search space was exhausted |
| `truncated` | boolean | Some eligible output was omitted |
| `reason` | enum | `complete`, `no_match`, `not_connected`, `max_depth`, `max_items`, `max_paths`, `max_expansions`, `context_budget` |
| `omitted_counts` | sorted object | Counts by category; null value means omission known but count unsafe to compute |
| `explored_nodes` | integer | Non-negative search evidence |
| `explored_edges` | integer | Non-negative search evidence |

Key states:

- Exhaustive disconnected search: complete, not truncated, `not_connected`.
- Search stopped by depth/expansion: incomplete, truncated, limiting reason.
- Complete search with capped output: complete, truncated, output limit reason.
- Unmatched selector: complete, not truncated, `no_match`.

## Directed paths

### DirectedPath

| Field | Type | Rule |
| --- | --- | --- |
| `rank` | integer | One-based result order |
| `node_ids` | string array | One more node than hops |
| `hops` | PathHop array | Contiguous and directionally valid |
| `ranking_policy` | string | `evidence_first_v1` |

### PathHop

| Field | Type | Rule |
| --- | --- | --- |
| `source_id` | string | Equals preceding path node |
| `target_id` | string | Equals following path node |
| `edge_id` | string | Canonical edge ID |
| `relationship` | string | Canonical relationship type |
| `direction` | enum | `forward` or `reverse` relative to stored edge |
| `evidence` | EvidenceReference | Required |

Paths are simple: no repeated node. Search transitions from `searching` to `connected`, `not_connected`,
or `limit_reached`; results are immutable after return.

## Context packages

### ContextPackage

| Field | Type | Rule |
| --- | --- | --- |
| `budget_kind` | string | `structural_record_v1` |
| `budget_limit` | integer | Equals requested context units |
| `budget_used` | integer | 0..budget limit |
| `items` | ContextItem array | Ranked and closure-safe |
| `omissions` | OmissionSummary array | Sorted by category |

### ContextItem

| Field | Type | Rule |
| --- | --- | --- |
| `rank` | integer | One-based selection order |
| `category` | enum | `target`, `ambiguity`, `node`, `relationship`, `diagnostic` |
| `distance` | integer | Non-negative graph distance |
| `cost_units` | integer | Exactly 1 in v1 |
| `subject_id` | string | Stable canonical ID |
| `summary` | object | Bounded canonical summary, not raw source text |
| `evidence` | EvidenceReference or null | Required for relationships/diagnostics |

An edge may be selected only if both endpoint summaries are already selected or fit atomically in the
remaining budget. Package state transitions are `ranking` → `packing` → `complete|budget_exhausted`.

## Errors

### IntelligenceError

| Field | Type | Rule |
| --- | --- | --- |
| `contract_version` | string | Best understood version or requested raw value |
| `category` | enum | `request`, `compatibility`, `state`, `integrity`, `internal` |
| `code` | string | Stable machine code |
| `message` | string | Actionable, no stack trace |
| `field` | string or null | Invalid request field when applicable |
| `retryable` | boolean | Stable retry guidance |

Codes: `invalid_request`, `invalid_parameter`, `missing_target`, `unsupported_operation`,
`unsupported_contract_version`, `unsupported_graph_schema`, `graph_not_ready`,
`graph_identity_mismatch`, `graph_integrity_error`, and `internal_error`.

No-match and ambiguity normally return successful results rather than errors.

## Relationships and ownership

```text
CodeGraph snapshot 1 ── 1 GraphIndex ── 1 IntelligenceKernel
IntelligenceRequest ── 1 IntelligenceBounds
IntelligenceResult ── 1 GraphIdentity
IntelligenceResult ── * TargetResolution
IntelligenceResult ── * DirectedPath ── * PathHop ── 1 EvidenceReference
IntelligenceResult ── 0..1 ContextPackage ── * ContextItem
```

The kernel and derived index never own or mutate canonical nodes, edges, diagnostics, or source files.
