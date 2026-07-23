# 2026-07-22 — Foundation and local dashboard

## Objective

Establish a dedicated MQL5-aware code intelligence repository that gives both humans and AI systems
an evidence-backed structural view of `.mq5` and `.mqh` projects.

## Starting state

- Repository: `C:\work\mql5-codegraph`
- Source used for real-world validation: `C:\work\Example-MQL5`
- Baseline commit: `39b56d26ff2f3aa638eb7cd7f01eeb86fb9b0e9d`
- Product version: `0.2.0`

## Work completed

- Built a tolerant MQL5 tokenizer and structural parser.
- Added repository include resolution, call resolution, ambiguity diagnostics, and MQL5 runtime edges.
- Added a deterministic canonical JSON graph with stable node and edge identifiers.
- Added CLI commands for analyze, status, query, context, impact, export, and serve.
- Added a loopback-only local HTTP API and interactive React/Cytoscape dashboard.
- Added symbol search, graph filtering, context focus, upstream impact, diagnostics, and source evidence.
- Added source containment, file-size limits, request-size limits, and security headers.
- Established Spec Kit specifications for the core analyzer and local dashboard.

## Decisions

- Preserve relationship origin and confidence instead of presenting inferred relationships as facts.
- Keep the product offline-first and bind the dashboard to `127.0.0.1` by default.
- Treat the canonical graph as backend-neutral; CLI, web, MCP, and future adapters consume the same model.
- Adopt [ADR-0001](../decisions/ADR-0001-intelligence-kernel.md): build an Intelligence Kernel before stabilizing the MCP API.

## Verification evidence

| Check | Method | Result |
| --- | --- | --- |
| Python regression suite | `python -m unittest discover -s tests` | 16/16 passed |
| Frontend quality | `npm run lint` | Passed with zero warnings |
| Frontend production build | `npm run build` | Passed |
| Real repository analysis | Dashboard against `C:\work\Example-MQL5` with MT5 include root | 26 files, 474 nodes, 3,441 edges |
| Browser smoke test | Search `OnTick`, focus context, trace impact, open source | Passed; zero console errors/warnings |
| Git baseline | Conventional Commit | `39b56d2 feat(core): build MQL5 code intelligence platform` |

## Risks and unresolved questions

- The parser is tolerant rather than a complete MetaEditor-compatible frontend.
- Macro expansion, complete type inference, dynamic dispatch, and runtime-generated names remain limited.
- Standard-library calls remain external unless their implementation source is indexed.
- Graph accuracy must improve before heuristic guardrails are enabled by default.
- Generated dashboard assets are intentionally ignored and must be built before packaging or serving a fresh clone.

## Product direction agreed

1. Intelligence Kernel and graph schema evolution.
2. MQL5 Structural Guardrails.
3. Critical Path engine and visualization.
4. Token-budgeted Context Packs.
5. Stable MCP server adapter; a read-only stdio alpha may be introduced earlier for contract testing.

## Next objective

Specify and implement `003 — MQL5 Intelligence Kernel & Structural Guardrails`, beginning with an internal
service boundary, finding model, rule interface, suppression policy, and a high-confidence golden test corpus.
