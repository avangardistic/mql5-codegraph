# 2026-07-22 — Graphify and project governance

## Objective

Make the repository durable across many development sessions by creating a project journal, an ADR
system, and a persistent Graphify knowledge graph that indexes both implementation and design intent.

## Starting state

- Branch: `main`
- Baseline commit: `39b56d26ff2f3aa638eb7cd7f01eeb86fb9b0e9d`
- Graphify: `graphifyy 0.9.20`
- No prior `graphify-out/graph.json` existed in this repository.

## Work completed

- Added a durable journal index, session template, and foundation entry.
- Added an ADR index and accepted ADR-0001 for the Intelligence Kernel boundary.
- Added root `AGENTS.md` governance so future sessions consistently load the journal, ADRs, and Graphify index.
- Indexed code, specifications, workflow documentation, ADRs, and journal records.
- Built the graph as directed so caller, dependency, and reference direction is preserved.
- Added human-readable labels for all detected communities.
- Exported GraphRAG JSON, an audit report, and standalone interactive HTML.

## Graph evidence

| Stage | Result |
| --- | --- |
| Corpus detection | 90 files, approximately 43,191 words at initial full scan |
| Structural extraction | 304 nodes, 735 raw edges |
| Semantic extraction | 94 nodes, 96 edges, 5 hyperedges |
| Merged extraction | 398 nodes, 831 raw edges |
| Directed graph | 398 nodes, 702 retained edges, 29 communities |

Semantic token counts are recorded as zero because the host-agent execution surface did not expose
per-agent usage to the Graphify chunk files. Zero therefore means “not available”, not “no model work”.

## Integrity findings

- Semantic chunks passed endpoint validation with no dangling edges.
- Graphify AST extraction emitted 98 import edges whose external module endpoints had no corresponding
  nodes; the directed builder omitted those dangling edges.
- The integrity gate also reported six exact duplicate edges and 36 same-endpoint directed edge
  collapses. The raw extraction is retained for audit; generated graph output must not be treated as a
  lossless multigraph until this upstream limitation is addressed.
- Seven configuration-only source files produced zero structural nodes. This is expected for files that
  contain metadata rather than symbols, but remains visible in the extraction log.

## Decisions

- Keep `graphify-out/` generated and ignored by Git; canonical decisions and session state live in tracked docs.
- Use a directed Graphify graph for architecture and dependency work.
- Run Graphify incremental update whenever tracked code, specs, ADRs, or journal entries materially change.
- Never use generated graph reports as higher authority than live source, tests, specifications, or ADRs.

## Verification evidence

| Check | Result |
| --- | --- |
| Semantic chunk 01 | 46 nodes, 54 edges, 3 hyperedges; valid endpoints |
| Semantic chunk 02 | 48 nodes, 42 edges, 2 hyperedges; valid endpoints |
| Community labeling | 29/29 communities labeled |
| HTML export | `graphify-out/graph.html` generated successfully |
| Integrity report | `graphify-out/health.json` generated; warnings documented above |

## Next objective

Create the feature specification for `003 — MQL5 Intelligence Kernel & Structural Guardrails`, including
schema migration, rule confidence tiers, suppression behavior, golden fixtures, and a read-only MCP alpha.
