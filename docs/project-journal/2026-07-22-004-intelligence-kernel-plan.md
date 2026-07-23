# 2026-07-22 — Intelligence Kernel implementation plan

## Objective

Produce the complete Phase 0/1 implementation design for Spec 003: research decisions, data model,
machine-checkable v1 contracts, Kernel structure, compatibility migration, and runnable validation guide.

## Starting state

- Branch: `main`
- Baseline commit: `39b56d26ff2f3aa638eb7cd7f01eeb86fb9b0e9d`
- Active feature: `specs/003-intelligence-kernel`
- Relevant decision: [ADR-0001](../decisions/ADR-0001-intelligence-kernel.md)
- Spec quality gate: 16/16 passed; implementation plan and Phase 0/1 artifacts did not yet exist.

## Work completed

- Added `plan.md` with technical context, pre/post constitution checks, source layout, and delivery sequence.
- Added `research.md` resolving Kernel boundaries, indexing, identity/versioning, matching, traversal,
  evidence-first path ranking, structural context budgeting, freshness, compatibility, and performance.
- Added `data-model.md` defining requests, bounds, identities, resolution, evidence, results, completion,
  directed paths, context packages, stable errors, relationships, validation, and state transitions.
- Added normative contracts for Intelligence Kernel v1, legacy/new CLI surfaces, legacy/new HTTP surfaces,
  and direct/CLI/HTTP conformance and migration gates.
- Added a Draft 2020-12 JSON Schema for normalized request, result, evidence, path, context, completion,
  and error envelopes.
- Added `quickstart.md` covering legacy compatibility, normalized CLI/HTTP operations, determinism,
  evidence, bounds, regression, and the opt-in 10,000-node performance gate.

## Decisions

- Keep `CodeGraph` canonical and backend-neutral; add a thin `IntelligenceKernel` over one immutable `GraphIndex`.
- Use Intelligence contract `1.0.0` independently from graph schema, package version, HTTP major, and snapshot revision.
- Preserve exact legacy CLI/Web commands, routes, JSON shapes, errors, defaults, and exit/status behavior.
- Add normalized operations only under a new CLI `intelligence` namespace and `/api/v1/intelligence/*` routes.
- Rank default directed paths by evidence quality before hop count so weak inference cannot outrank a trustworthy route.
- Use provider-neutral `structural_record_v1` context units; raw source excerpts remain outside v1 context packages.
- Do not deprecate or remove existing `CodeGraph` traversal helpers during feature 003.

## Verification evidence

| Check | Command or method | Result |
| --- | --- | --- |
| Spec Kit setup | `.specify/scripts/powershell/setup-plan.ps1 -Json` | Resolved Spec 003 and created plan target |
| Graphify architecture query | BFS over 12 graph-vocabulary tokens | Confirmed direct CodeGraph coupling from CLI/Web and ADR thin-adapter boundary |
| Required artifacts | Python path check | 9/9 Phase 0/1 files present |
| JSON syntax | `python -m json.tool` | Passed |
| JSON Schema | `Draft202012Validator.check_schema` | Passed |
| Placeholders | `rg` for template and clarification markers | No unresolved marker in plan artifacts |
| Patch integrity | `git diff --check` | Passed |
| Graphify incremental/health | Directed incremental merge and `diagnose_extraction` | 503 nodes, 806 edges; 0 missing, dangling, duplicate, self-loop, or directed-collapse edges |

No source behavior changed, so runtime tests were not executed in this design-only session.

## Risks and unresolved questions

- Per-file evidence staleness cannot be proven from the current canonical graph; v1 reports `unknown`
  unless an optional safe evidence probe is supplied.
- Diagnostic-to-symbol association may initially be location-based because diagnostics lack canonical subject IDs.
- The reference Windows machine and power profile must be captured before claiming the one-second performance criterion.
- Dense path search remains inherently expensive and depends on mandatory `max_expansions` enforcement.
- The graph has one endpoint pair that would collapse if treated as undirected; directed mode retains both semantics.

## Next objective

Generate dependency-aware `tasks.md`, run Spec Kit cross-artifact analysis, remediate any critical/high gaps,
then request approval before implementing feature 003.
