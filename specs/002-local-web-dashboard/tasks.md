# Tasks: Local Web Dashboard

## Phase 1: Setup

- [x] T001 Adapt the official Sites starter into a local Vite application in `web/package.json` and `web/vite.config.ts`
- [x] T002 [P] Add frontend and generated-asset ignore/package rules in `.gitignore` and `pyproject.toml`
- [x] T003 [P] Add dashboard product documentation in `README.md` and `docs/web-dashboard.md`

## Phase 2: Foundational

- [x] T004 Implement thread-safe graph and job state in `src/mql5_codegraph/web/state.py`
- [x] T005 Implement safe query parsing, projection, diagnostics, and source evidence in `src/mql5_codegraph/web/api.py`
- [x] T006 Implement loopback HTTP/static server lifecycle in `src/mql5_codegraph/web/server.py`
- [x] T007 Add `serve` command and options in `src/mql5_codegraph/cli.py`

## Phase 3: User Story 1 - Visual repository analysis

- [x] T008 [P] [US1] Add state and analyze API tests in `tests/test_web_state.py` and `tests/test_web_api.py`
- [x] T009 [P] [US1] Build dashboard shell, metrics, analysis form, and responsive states in `web/src/App.tsx`
- [x] T010 [US1] Build interactive graph canvas and filters in `web/src/components/GraphWorkspace.tsx`
- [x] T011 [US1] Connect job polling and graph projection in `web/src/api.ts` and `web/src/App.tsx`

## Phase 4: User Story 2 - Search, context, and impact

- [x] T012 [P] [US2] Add query/context/impact API contract tests in `tests/test_web_api.py`
- [x] T013 [US2] Build command search and result focus flow in `web/src/components/SearchPalette.tsx`
- [x] T014 [US2] Build node inspector, context, and impact views in `web/src/components/Inspector.tsx`

## Phase 5: User Story 3 - Diagnostics and source evidence

- [x] T015 [P] [US3] Add diagnostic and source traversal tests in `tests/test_web_api.py`
- [x] T016 [US3] Build diagnostics explorer in `web/src/components/DiagnosticsPanel.tsx`
- [x] T017 [US3] Build source evidence viewer in `web/src/components/SourceViewer.tsx`

## Phase 6: Polish and validation

- [x] T018 Finish product visual system, keyboard access, and narrow layout in `web/src/styles.css`
- [x] T019 Build frontend into `src/mql5_codegraph/web_static/` and run Python/Node verification
- [x] T020 Run dashboard on `C:\work\Example-MQL5`, perform browser smoke verification, and update `docs/web-dashboard.md`

## Dependencies & Execution Order

- Setup precedes server and UI work.
- T004-T007 establish the API contract used by every story.
- US1 delivers the first usable dashboard; US2 and US3 then extend independent panels.
- Frontend components marked `[P]` may be developed against the documented HTTP contract.

## Implementation Strategy

First make the server and analyze flow correct under tests. Then deliver one coherent dashboard viewport,
add query/impact and evidence panels, and finish with production build plus real-repository verification.
