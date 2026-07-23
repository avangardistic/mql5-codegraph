# CLI Compatibility Contract

## Frozen legacy surface

Feature 003 must preserve these commands, arguments, defaults, human output intent, JSON top-level shapes,
stderr behavior, and exit codes:

| Command | Legacy JSON shape |
| --- | --- |
| `analyze` | Object: output, files, nodes, edges, diagnostics, source_fingerprint |
| `status` | Object: schema_version, files, nodes, edges, diagnostics, source_fingerprint |
| `query` | Bare node array |
| `context` | Bare `{nodes, edges}` object |
| `impact` | Bare array of `{node, distance, edge_path}` |
| `export` | Object: format, resolved output, nodes, edges |
| `serve` | Existing local dashboard startup behavior |

- Success returns 0.
- Handled load/schema/I/O errors return 1 and write `error: ...` to stderr.
- Missing symbols in legacy context/impact return 2 and write the existing message to stderr.
- Argument errors remain argparse exit 2.
- Legacy context depth defaults to 1; impact defaults to 3. CLI's historical bounds are projected explicitly
  and must not silently adopt stricter v1 defaults.
- Legacy CLI symbol resolution remains name-based where exact node-ID support would change behavior.

Golden tests are authoritative. Feature 003 adds no deprecation warning to stdout or stderr.

## New normalized namespace

```text
mql5-codegraph intelligence <operation> <graph.json> ...
    --contract-version 1 --json
```

Operations: `query`, `context`, `impact`, `diagnostics`, `path`, `context-package`.
Normalized commands emit the v1 result or error envelope. New `path` and `context-package` operations
exist only in this namespace during feature 003.

Example:

```text
mql5-codegraph intelligence path graph.json OnTick CalculateLots \
  --max-depth 5 --max-paths 3 --max-expansions 10000 --contract-version 1 --json
```

## Legacy projection rules

- Query projects `result.nodes` to the historical bare array.
- Context projects nodes and relationships to `{nodes, edges}` and removes v1 metadata.
- Impact projects each normalized entry to `{node, distance, edge_path}`, retaining edge IDs only.
- Kernel no-match/ambiguity is translated to the exact legacy missing-symbol behavior where required.
- Adapter-only fields never enter kernel semantic equality.

During migration, tests dual-run old and kernel paths and compare both normalized semantics and exact legacy bytes.
