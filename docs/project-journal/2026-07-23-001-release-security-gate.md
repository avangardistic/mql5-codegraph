# 2026-07-23 — Release and security gate

## Objective

Run the v0.2.0 release gate, audit source and dependencies, decide the measured slow-drip risk, apply
proportionate hardening, and leave one verified clean commit.

## Starting state

- Branch and commit: `main` at `c5cba80 fix(web): bound idle request reads`
- Relevant specification: `specs/003-intelligence-kernel/spec.md`
- Known constraints: local single-user alpha, unauthenticated loopback dashboard, generated Graphify/build
  output must remain uncommitted, and existing feature/governance documentation was intentionally dirty.

## Work completed

- Completed repository-wide security scan `1582fe20-490b-4737-8667-b47d74333eff` over the locked starting
  revision: 39 deployed first-party files reviewed from a deterministic 231-row inventory, 30 canonical
  candidates validated, and six low-severity findings reported. No critical, high, or medium finding survived.
- Measured two slow-drip clients retaining both request slots despite the two-second idle timeout. Classified
  the bottleneck as blocking network I/O plus the finite request semaphore, not CPU, and added a ten-second
  absolute deadline around the request line, headers, and declared body.
- Restricted the unauthenticated dashboard to loopback binds, validated request `Host` and browser `Origin`,
  and stopped saved graph metadata from implicitly authorizing source-viewer filesystem access.
- Rejected absolute, drive-qualified, UNC, and canonically escaping include targets before filesystem probes;
  source discovery now ignores resolved paths outside the repository.
- Removed the lexer's quadratic line-prefix rescan by tracking whether the current line already contains
  non-whitespace content.
- Updated Vite to 8.1.5, refreshed transitive Node dependencies, raised the build-system floor to
  `setuptools>=83`, and migrated the package license field to its non-deprecated SPDX string form.
- Added regression coverage for slow-drip release, loopback and origin controls, optional saved-graph roots,
  include containment, escaping symlinks, and long leading-whitespace preprocessing.
- Recorded the dashboard boundary in
  [ADR-0002](../decisions/ADR-0002-local-dashboard-security-boundary.md) and marked Feature 003 implemented.

## Decisions

- Accept four remaining low-severity adversarial scaling findings only for the offline local alpha:
  parser range-membership rescans, nested argument rescans, binding-list rescans, and ambiguous call-edge
  fan-out. Hosted or multi-tenant ingestion remains gated on explicit work budgets or linear-time structures.
- Use the existing finite threaded server with an absolute request-read deadline; no framework or runtime
  dependency is justified by the measured slow-drip bottleneck.
- Treat remote dashboard access as a future authenticated adapter/proxy boundary, not an insecure
  `--host 0.0.0.0` option.
- Prefer focused local remediation for the six independent low findings. The scan's structural-hardening
  review found no cross-cutting redesign proportionate to the supported product boundary.

## Verification evidence

| Check | Command or method | Result |
| --- | --- | --- |
| Focused regressions | `python -m unittest tests.test_lexer tests.test_indexer tests.test_web_state tests.test_web_api` | 30 passed in 4.243s |
| Full Python suite | `python -m unittest discover -s tests` | Final run: 92 passed in 6.821s |
| Python compilation | `python -m compileall -q src tests tools` | Exit 0 |
| Frontend install | `npm ci` in `web/` | 173 packages audited; 0 vulnerabilities |
| Frontend lint | `npm run lint` in `web/` | Exit 0; no warnings |
| Frontend build | `npm run build` in `web/` | Vite 8.1.5 production build passed in 487ms |
| Node dependency audit | `npm audit --json` and `npm audit --omit=dev --json` | 0 vulnerabilities across full and production graphs |
| Python build dependency audit | `uvx --from pip-audit pip-audit -r <setuptools>=83 requirement>` | No known vulnerabilities |
| Distribution build | `uvx --from build pyproject-build` | sdist and wheel built without warnings |
| Distribution metadata | `uvx --from twine twine check dist\*` | Wheel and sdist passed |
| Wheel contents | Standard-library ZIP inspection | 11 dashboard files present, including HTML, JavaScript, and CSS |
| Intelligence benchmark | `MQL5_CODEGRAPH_PERF=1 python tools/benchmark_intelligence.py` | 10k nodes/40k edges; overall p95 29.3942ms, max 42.2318ms; threshold passed |
| Lexer scaling probe | 50k/100k/200k leading spaces, seven-run median | 3.6591/7.4942/16.1917ms; approximately linear |
| Slow-drip regression | Two slots, 200ms idle timeout, 500ms absolute deadline, 50ms byte drip | Health request automatically released and returned HTTP 200 |
| Browser smoke | Playwright CLI against fixture dashboard | 16 nodes, 22 edges, search/context/source viewer passed; API 200; 0 console errors/warnings |
| Security scan | Codex Security repository scan and canonical finalizer | 6 low; 0 critical/high/medium; report and hardening portfolio generated |
| Directed project graph | Incremental Graphify semantic/code update and multigraph diagnostic | 1,435 nodes, 2,687 directed edges; 0 missing/dangling/self-loop/duplicate/collapsed edges |

## Risks and unresolved questions

- Four low-severity parser/resolver amplification paths remain deliberately open for the local alpha and
  block any claim that untrusted hosted ingestion is production-ready.
- The security scan did not contact an SMB endpoint; the resolver fix removes the validated UNC probe path
  without reproducing workstation authentication behavior.
- Platform safety filters blocked derived long-form finding write-up workers. Canonical findings retain the
  validated source, sink, attack path, remediation, and tests; this did not reduce scan coverage.
- Completed analysis work still has no universal wall-clock deadline. Request-read bounds and Intelligence
  Kernel traversal bounds do not replace an analyzer-wide work budget.
- Graphify re-clustering changed the community set and auto-renamed affected communities by their hub.
  Directed graph integrity is clean; an optional LLM label refresh remains cosmetic follow-up.

## Next objective

Define a versioned analyzer work-budget contract and add the first bounded regression for parser
range-membership processing before considering hosted untrusted-repository ingestion.
