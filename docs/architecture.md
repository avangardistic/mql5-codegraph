# Architecture

The pipeline is intentionally layered:

```text
source discovery -> lexer -> structural parser -> repository resolver
                 -> MQL5 runtime enrichment -> canonical graph -> adapters/CLI
```

The lexer owns source fidelity and recovery. The parser extracts declarations and call sites without
requiring complete source. The resolver works across all parsed files, resolves includes and symbols,
and records ambiguity rather than inventing certainty. Runtime enrichment adds terminal-driven event
edges with `origin=runtime`. Exporters depend only on the canonical graph model.

Every relationship contains an origin and confidence. `calls` means a visible call expression;
`runtime_dispatches` means the terminal invokes a valid event entry point; `may_trigger_event` records
a documented runtime consequence rather than a direct call.
