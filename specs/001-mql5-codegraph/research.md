# Research: MQL5 CodeGraph MVP

## Decision: Tolerant tokenizer and structural parser for the MVP

**Rationale**: No mature, verified MQL5 grammar is assumed available. A dedicated tokenizer prevents
comments and strings from corrupting brace/call analysis, while a recovery-oriented structural parser
delivers useful graphs before full compiler-grade parsing exists.

**Alternatives considered**: Treating files as C++, regex-only extraction, and blocking the MVP on a
complete Tree-sitter grammar. C++ parsing misses MQL5 runtime semantics; regex alone is too fragile;
full grammar development would delay the usable indexing loop.

## Decision: Two-pass repository resolution

**Rationale**: First collect declarations and include relationships, then resolve calls against the
repository-wide symbol table. This supports forward declarations and cross-file calls while preserving
unresolved calls as honest diagnostics.

**Alternatives considered**: Single-pass resolution and compiler integration. Single-pass order affects
results; MetaEditor does not expose a stable public AST contract for this tool.

## Decision: Canonical JSON plus adapter exports

**Rationale**: Stable local JSON is inspectable, diffable, backend-neutral, and usable by agents without
running a graph database. GraphML demonstrates that exporters can be added without parser coupling.

**Alternatives considered**: Neo4j as mandatory storage and Graphify-native storage. Both add operational
coupling before the MQL5 extraction quality is proven.

## Decision: Explicit MetaTrader runtime edges

**Rationale**: Event handlers are invoked by the terminal, not by visible source calls. Runtime edges
make execution flow discoverable without falsifying static call relationships.

**Alternatives considered**: Leaving handlers as roots or creating synthetic CALLS edges. Both lose
meaning; synthetic calls misrepresent evidence.
