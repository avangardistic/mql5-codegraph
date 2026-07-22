# Known Limitations and Roadmap

The MVP is a tolerant structural analyzer, not a MetaEditor compiler frontend.

- Macro bodies and conditional compilation are recorded but not fully expanded.
- Overload resolution uses scope and arity hints, not complete MQL5 type inference.
- Template-like constructs and complex declarators may be recovered only partially.
- Standard-library calls are represented as external nodes unless their source is included in scope.
- Dynamic dispatch, function pointers, reflective indicator loading, and runtime-generated names are
  not resolved statically.

Planned milestones include a formal Tree-sitter MQL5 grammar, richer type inference, incremental
indexing, Graphify/Neo4j adapters, an MCP server, and compile-diagnostic correlation with MetaEditor.
