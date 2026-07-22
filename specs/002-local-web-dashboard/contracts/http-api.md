# Local HTTP API Contract

All responses use JSON except static assets and `GET /api/source`, which still returns a JSON envelope.
Errors use `{ "error": { "code": string, "message": string } }`. Request bodies are capped at 64 KiB.

## `GET /api/health`

Returns service version, readiness, graph availability, graph version, and active job identifier.

## `GET /api/status`

Returns active root, graph summary, diagnostic counts, active job, and recent jobs.

## `POST /api/analyze`

Body: `{ "root": string, "include_roots": string[] }`.

Returns `202` with the queued job. Returns `409` when analysis is already running and `400` for invalid paths.

## `GET /api/jobs/{id}`

Returns one analysis job or `404`.

## `GET /api/graph`

Query: repeated `kind`, repeated `relationship`, optional `q`, and `limit` from 1 to 2000.
Returns a bounded visualization graph. Nodes required by included edges are preserved within the cap.

## `GET /api/query`

Query: required `q`, optional `kind`, `limit` from 1 to 100.

## `GET /api/context` and `GET /api/impact`

Query: required `symbol`, `depth` from 0 to 5. Context returns a bounded neighborhood; impact returns
upstream entries with edge paths.

## `GET /api/diagnostics`

Query: optional `severity`, `code`, and `limit` from 1 to 1000. Returns filtered items and aggregate counts.

## `GET /api/source`

Query: required repository-relative `file`, optional positive `line`. Only existing `.mq5`/`.mqh` files
contained by the active root and no larger than 2 MiB are returned.
