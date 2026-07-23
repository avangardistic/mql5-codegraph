# Conformance and Migration Contract

## Equivalence matrix

| Operation | Direct kernel | CLI v1 | HTTP v1 | Legacy CLI | Legacy HTTP |
| --- | --- | --- | --- | --- | --- |
| Query | normalized | identical normalized | identical normalized | frozen projection | frozen projection |
| Context | normalized | identical normalized | identical normalized | frozen projection | frozen projection |
| Impact | normalized | identical normalized | identical normalized | frozen projection | frozen projection |
| Diagnostics | normalized | identical normalized | identical normalized | N/A | frozen projection |
| Path | normalized | identical normalized | identical normalized | N/A | N/A |
| Context package | normalized | identical normalized | identical normalized | N/A | N/A |

Transport-only values such as client request ID and HTTP snapshot revision are excluded before semantic
comparison. All other fields, array order, evidence, limits, and completion metadata must agree.

## Required vectors

- Exact ID, qualified name, short name, substring, no match, and equal-ranked ambiguity.
- Extracted, resolved, runtime, inferred, locationless, stale, unavailable, and unknown evidence.
- Directed connection, disconnected graph, cycle, equal-ranked alternatives, reverse direction.
- Every depth/item/path/expansion/context bound, including zero depth and atomic packing.
- Unsupported contract major, unsupported graph schema, fingerprint mismatch, malformed request.
- Reversed/randomized graph insertion order with byte-identical normalized output over 100 repetitions.
- Read-only graph/source before and after every operation.

## Migration gates

1. Capture legacy golden outputs before changing adapters.
2. Kernel unit and serialization tests pass independently.
3. Dual-run normalized semantics match the old implementation for supported legacy operations.
4. Legacy projectors produce exact historical JSON/stderr/exit/status behavior.
5. CLI v1 and HTTP v1 match direct-kernel results.
6. Existing full regression suite and compileall pass.
7. Reference fixture end-to-end and opt-in 10k benchmark pass.

No legacy method, command, field, or route is removed in feature 003.

## Performance protocol

- Generate exactly 10,000 nodes and approximately 40,000 edges in memory from a fixed seed.
- Include cycles, disconnected components, ambiguous names, runtime/inferred edges, and known paths.
- Build `GraphIndex` before timing.
- Run 20 untimed warmups and at least 200 fixed mixed requests.
- Measure with `perf_counter_ns`; report nearest-rank p50, p95, max and operation counts.
- Validate every response during timing.
- Record Python, OS, CPU, logical CPU count, power-profile note, graph size, and request mix.
- Enforce p95 below one second only when `MQL5_CODEGRAPH_PERF=1`; ordinary CI runs reduced correctness cases.
