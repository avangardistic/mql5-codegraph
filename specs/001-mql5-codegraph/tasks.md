# Tasks: MQL5 CodeGraph MVP

**Input**: Design documents from `specs/001-mql5-codegraph/`

## Phase 1: Setup

- [x] T001 Create Python project metadata and ignore rules in `pyproject.toml` and `.gitignore`
- [x] T002 [P] Document architecture and usage in `README.md` and `docs/architecture.md`
- [x] T003 [P] Create MQL5 reference fixtures in `tests/fixtures/basic_ea/`

## Phase 2: Foundational

- [x] T004 Create versioned graph entities and deterministic serialization in `src/mql5_codegraph/graph.py`
- [x] T005 [P] Create diagnostic entities and codes in `src/mql5_codegraph/diagnostics.py`
- [x] T006 Create MQL5 tokenizer with source spans in `src/mql5_codegraph/lexer.py`
- [x] T007 Create tolerant structural parser in `src/mql5_codegraph/parser.py`

## Phase 3: User Story 1 - Index an MQL5 repository (P1)

**Independent Test**: Analyze `tests/fixtures/basic_ea` and assert declarations, calls, includes,
runtime dispatch, and diagnostics.

- [x] T008 [P] [US1] Add lexer and parser tests in `tests/test_lexer.py` and `tests/test_parser.py`
- [x] T009 [US1] Implement include and call resolution in `src/mql5_codegraph/resolver.py`
- [x] T010 [US1] Implement MetaTrader event enrichment in `src/mql5_codegraph/runtime.py`
- [x] T011 [US1] Implement repository discovery and analysis pipeline in `src/mql5_codegraph/indexer.py`
- [x] T012 [US1] Add end-to-end index assertions in `tests/test_indexer.py`

## Phase 4: User Story 2 - Explore and assess impact (P2)

**Independent Test**: Run query, context, and impact against a saved fixture graph.

- [x] T013 [P] [US2] Define CLI parser and structured result helpers in `src/mql5_codegraph/cli.py`
- [x] T014 [US2] Implement analyze, status, query, context, and impact commands in `src/mql5_codegraph/cli.py`
- [x] T015 [US2] Add CLI integration tests in `tests/test_cli.py`

## Phase 5: User Story 3 - Export to graph tools (P3)

**Independent Test**: Export GraphML and compare canonical IDs to the source JSON graph.

- [x] T016 [P] [US3] Implement GraphML adapter in `src/mql5_codegraph/exporters/graphml.py`
- [x] T017 [US3] Connect the export command in `src/mql5_codegraph/cli.py`
- [x] T018 [US3] Add GraphML contract coverage in `tests/test_cli.py`

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T019 Run all automated tests and quickstart commands from `specs/001-mql5-codegraph/quickstart.md`
- [x] T020 Record known limitations and roadmap in `docs/limitations.md`

## Dependencies & Execution Order

- Phase 1 precedes Phase 2.
- T004-T007 establish the contracts required by every user story.
- US1 is the MVP and precedes CLI traversal in US2.
- US3 depends only on the canonical graph and CLI command framework.
- Tasks marked `[P]` touch separate files and may be executed concurrently.

## Implementation Strategy

Deliver US1 first as a usable offline indexer. Add traversal commands without changing the graph
schema, then prove adapter independence with GraphML. Complete only after the fixture, malformed-source
case, deterministic serialization, and quickstart all pass.
