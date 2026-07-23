# 2026-07-22 — Intelligence Kernel specification

## Objective

Define feature 003 as the backend-neutral Intelligence Kernel that future MCP, structural guardrail,
context augmentation, and critical-path features can share without duplicating graph semantics.

## Starting state

- Branch: `main`
- Baseline commit: `39b56d26ff2f3aa638eb7cd7f01eeb86fb9b0e9d`
- Relevant decision: [ADR-0001](../decisions/ADR-0001-intelligence-kernel.md)
- Existing CLI, dashboard, and exporters consumed `CodeGraph` directly.
- Graphify trace identified `CodeGraph` as a 33-degree bridge between analysis producers and adapters.

## Work completed

- Added `specs/003-intelligence-kernel/spec.md` with three independently testable user stories:
  consistent cross-interface intelligence, evidence-backed directed path tracing, and bounded AI context.
- Added 16 functional requirements covering authoritative semantics, provenance, deterministic ordering,
  bounded traversal, ambiguity, schema compatibility, read-only behavior, and regression protection.
- Added measurable success criteria for interface conformance, evidence completeness, determinism,
  bounds, reference-scale response time, and compatibility.
- Added and completed the Spec Kit requirements-quality checklist.
- Updated `.specify/feature.json` so downstream plan and task commands resolve feature 003.

## Decisions

- Feature 003 is limited to the Intelligence Kernel instead of combining the kernel with the structural
  guardrail catalog. This preserves the dependency order established by ADR-0001.
- Stable MCP tools, concrete guardrail rules, prompt templates, and critical-path visualization remain
  separate consumer features.
- `CodeGraph` remains the canonical data model. Intelligence orchestration will wrap it rather than
  expanding it into an adapter-aware service.
- Pure representation exporters may continue consuming the canonical graph directly when they do not
  reinterpret analysis semantics.

## Verification evidence

| Check | Command or method | Result |
| --- | --- | --- |
| Spec placeholders | `rg` for template and clarification markers | No unresolved markers in `spec.md`; checklist contains only its required marker label |
| Patch integrity | `git diff --check` | Passed |
| Spec quality | Manual Spec Kit checklist validation | 16/16 items passed on iteration 1 |
| Graphify incremental update | Two directed incremental passes and HTML export | Final graph 455 nodes and 759 edges; manifest clean after journal evidence refresh |
| Graph health | `diagnose_extraction(..., directed=True)` | 0 missing, dangling, self-loop, duplicate, or directed-collapse edges |
| Graphify query smoke | `graphify explain "Intelligence Kernel Feature"` | Feature node indexed with 3 evidence-backed connections |

## Risks and unresolved questions

- Planning must define normalized result envelopes and compatibility without leaking adapter-specific payloads into the kernel.
- The reference machine and fixture for the 10,000-node performance criterion must be documented in the plan.
- A deterministic structural context budget is specified, but its exact units and ranking rules remain a planning decision.
- The health diagnostic reports one endpoint pair that would collapse in an undirected graph and ten
  producer suppression sites; the retained directed graph has zero collapsed edges.

## Next objective

Create and review the implementation plan, research decisions, data model, and versioned contracts for feature 003.
