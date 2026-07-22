# Research: Local Web Dashboard

## Decision: Same-origin local server

**Rationale**: A single loopback origin simplifies security, avoids permissive CORS, and lets the
installed Python CLI serve both the production frontend and graph API. Source never leaves the machine.

**Alternatives considered**: Hosted dashboard, Electron, and separate production servers. Hosting
cannot read local repositories safely; Electron adds packaging cost; separate origins add avoidable risk.

## Decision: React visualization client with bounded Cytoscape projection

**Rationale**: Cytoscape provides mature pan/zoom/layout/selection interactions. The backend retains
the canonical graph and sends filtered, capped projections so browser rendering does not define analysis scale.

**Alternatives considered**: Canvas renderer built from scratch, SVG, and server-rendered diagrams.
They respectively increase interaction risk, degrade on large graphs, or lose exploratory behavior.

## Decision: Standard-library Python HTTP API

**Rationale**: The existing tool has no runtime dependencies. A carefully bounded `ThreadingHTTPServer`
preserves simple installation while supporting background analysis and same-origin static files.

**Alternatives considered**: FastAPI and Flask. Both are viable later, but the current API surface is
small and does not justify expanding the trusted runtime dependency set.

## Decision: Background job with immutable snapshots

**Rationale**: Indexing must not block UI requests. One active job at a time avoids CPU and state races;
the completed graph replaces the prior snapshot atomically.

**Alternatives considered**: Synchronous POST and unrestricted job concurrency. Both harm reliability.
