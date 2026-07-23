# Phase 0 Research: Intelligence Kernel

## Evidence base

Research used the current `CodeGraph`, CLI, Web API/state, tests, Spec 003, ADR-0001, project
constitution, and the directed Graphify index. Graphify confirmed that `CodeGraph` is the bridge between
analysis producers and CLI/Web/export consumers, and that semantic traversal is currently duplicated
across the canonical model and adapters.

## Decision 1 — Kernel boundary and package shape

**Decision**: Add `mql5_codegraph.intelligence` above `CodeGraph`. `IntelligenceKernel` is a thin
read-only façade; frozen contracts, indexing, matching, traversal, paths, and context selection live in
focused modules. It imports no adapter, parser, exporter, database, or visualization code.

**Rationale**: This provides one semantic authority without turning the canonical graph into a god
service. Pure functions remain testable and future MCP can consume the same boundary.

**Alternatives considered**:

- Add all operations to `CodeGraph`: rejected because it couples the backend-neutral model to use cases.
- Create one large `intelligence.py`: rejected because contract, indexing, and algorithms change for different reasons.
- Let CLI/Web implement new features independently: rejected because current symbol/depth semantics already diverge.

## Decision 2 — Immutable graph snapshot and derived index

**Decision**: Construct one immutable `GraphIndex` for each published `CodeGraph` snapshot. It stores
sorted node/name indexes, incoming/outgoing adjacency, relationship groups, and diagnostic indexes.
CLI builds one kernel per invocation; `DashboardState` atomically publishes graph, root, revision, and kernel.

**Rationale**: Current traversal scans all edges for each request. An O(V+E) snapshot build makes bounded
operations predictable and ensures a Web request cannot observe half of a re-index.

**Alternatives considered**:

- Rebuild adjacency on every operation: rejected for the 10,000-node target.
- Mutate `CodeGraph` with caches: rejected because it weakens read-only and deterministic model semantics.
- Copy the graph per request: rejected for latency and memory cost.

## Decision 3 — Independent contract and graph identities

**Decision**: Start the Intelligence contract at `1.0.0`, independent of canonical graph schema
`1.0.0`, package version, HTTP major, and dashboard revision. Every result reports graph schema,
`source_fingerprint`, and optional process-local snapshot revision.

**Rationale**: Storage compatibility and intelligence-result semantics evolve independently. A caller
may supply an expected fingerprint to reject stale work.

**Alternatives considered**:

- Reuse graph schema version: rejected because envelope changes would force graph migrations.
- Use dashboard revision as portable identity: rejected because it resets per process.
- Add random request IDs: rejected from canonical output; an optional client ID may be echoed but never affects equality.

## Decision 4 — Deterministic target resolution

**Decision**: Rank matches by exact node ID, exact qualified name, exact short name, then substring.
Preserve all equally ranked candidates and sort by match rank, qualified name case-fold, kind, and ID.

**Rationale**: Web currently accepts node IDs while CLI does not. The kernel needs one honest normalized
resolution while compatibility projectors retain legacy differences where required.

**Alternatives considered**:

- Pick the first candidate: rejected because it discards ambiguity.
- Add fuzzy/embedding search: deferred because it adds nondeterminism and dependencies.

## Decision 5 — Bounded traversal and completion semantics

**Decision**: Context uses deterministic BFS; impact uses reverse BFS over an explicit relationship
policy. Requests separately bound depth, items, paths, and expansions. Results distinguish complete,
not matched, not connected, output truncated, and search stopped by a bound.

**Rationale**: A single `truncated` flag cannot tell users whether the graph was exhaustively searched.
Sorted seeds, adjacency, and IDs make equal requests reproducible.

**Alternatives considered**:

- One global limit: rejected because output size and search effort are different risks.
- Unbounded traversal: rejected because cycles/dense graphs can exhaust memory or time.

## Decision 6 — Evidence-first directed path ranking

**Decision**: Enumerate bounded simple directed paths with a deterministic priority queue. Rank by:

1. fewer inferred/ambiguous hops;
2. fewer stale/unavailable evidence references;
3. fewer total hops;
4. lower origin penalty (`extracted=0`, `resolved=1`, `runtime=1`, `inferred=3`);
5. higher minimum confidence in integer basis points;
6. lexical edge-ID sequence.

**Rationale**: A one-hop inference must not silently outrank a slightly longer evidence-backed MQL5
execution route. Runtime dispatch is explicit domain evidence, not a source-code call, and remains labeled.

**Alternatives considered**:

- Shortest path first: rejected as the default because it can privilege weak inference.
- Enumerate all paths: rejected as exponential.
- NetworkX: rejected because the standard library is sufficient and explicit ordering is easier to audit.

## Decision 7 — Structural context budget

**Decision**: Use `structural_record_v1`: each emitted node summary, relationship/evidence record,
diagnostic, or ambiguity alternative costs one unit. Atomic groups prevent an edge without both endpoint
summaries. Ranking is target alternatives, direct evidence, local diagnostics, second-order evidence,
then remaining diagnostics; ties use distance, origin penalty, descending confidence, and stable ID.

**Rationale**: Structural units are deterministic, offline, provider-neutral, and easy to test. Every
package reports budget used and omissions by category.

**Alternatives considered**:

- Model tokens: rejected because tokenizer/provider specific.
- UTF-8 bytes or characters: rejected because metadata/language length biases relevance and complicates atomic groups.
- Source excerpts in v1: deferred; v1 returns summaries and evidence references only.

## Decision 8 — Evidence freshness

**Decision**: Evidence state is explicit: `available`, `stale`, `unavailable`, `unknown`, or
`not_applicable`, with a stable reason. Kernel accepts an optional read-only evidence probe; without one,
it reports `unknown` rather than inferring freshness from a stored location.

**Rationale**: A source location alone cannot prove that a file still matches the indexed graph.
The kernel must not import filesystem-security policy or claim false freshness.

**Alternatives considered**:

- Treat every location as available: rejected as misleading.
- Read files directly in the kernel: rejected because it violates backend neutrality and root containment.
- Add per-file hashes now: deferred to a canonical graph schema feature.

## Decision 9 — Compatibility and public surfaces

**Decision**: Freeze all current CLI commands, exit codes, stderr patterns, unversioned HTTP routes,
status/error codes, and JSON shapes. Migrate them through explicit projectors. Add normalized operations
under `mql5-codegraph intelligence ... --contract-version 1` and `POST /api/v1/intelligence/<operation>`.

**Rationale**: Existing scripts and dashboard code must continue working. New surfaces can be strict and
versioned without silently changing legacy payloads.

**Alternatives considered**:

- Replace legacy payloads with v1 envelopes: rejected as breaking.
- Add fields to unversioned responses: rejected because strict consumers may fail.
- Generic `/execute`: rejected because per-operation validation and documentation are clearer.

## Decision 10 — Verification and performance

**Decision**: Use stdlib `unittest`, exact golden JSON, randomized insertion-order determinism, 100-repeat
serialization checks, evidence/completion truth tables, legacy and normalized adapter conformance, and
read-only before/after graph serialization. Build a deterministic synthetic 10,000-node/~40,000-edge
benchmark with 20 warmups and at least 200 mixed requests; timing assertions are opt-in via
`MQL5_CODEGRAPH_PERF=1` and record the reference machine.

**Rationale**: Correctness must be stable in ordinary CI; hardware-sensitive latency claims need a
controlled local/release gate. The benchmark validates results as well as speed.

**Alternatives considered**:

- Commit a large graph fixture: rejected for repository bloat.
- Enforce wall-clock timing in every CI run: rejected as noisy across hardware.
- Benchmark without correctness assertions: rejected because fast wrong results are not success.

## Resolved assumptions and retained risks

- `max_depth=0` means targets only, preserving current Web semantics.
- Context default direction is `both`, preserving current neighborhood behavior.
- Legacy CLI compatibility is byte/shape-sensitive for JSON and stderr, not merely conceptual.
- Diagnostics may initially associate with symbols by location; imperfect associations remain explicit.
- Dense path search remains bounded by mandatory `max_expansions`.
- Per-file staleness cannot be proven until an evidence probe or future file fingerprint is available.
- The performance reference machine and power profile must be captured by the benchmark output before SC-005 is claimed.
