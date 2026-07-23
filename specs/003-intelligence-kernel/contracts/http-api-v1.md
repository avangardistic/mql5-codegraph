# HTTP API v1 and Legacy Compatibility

## Frozen unversioned routes

The dashboard remains on its current routes and payloads during feature 003:

`/api/health`, `/api/status`, `/api/analyze`, `/api/jobs/{id}`, `/api/graph`, `/api/query`,
`/api/context`, `/api/impact`, `/api/diagnostics`, and `/api/source`.

Existing query bounds, status codes, error codes, source containment, `.mq5/.mqh` allow-list, 2 MiB cap,
and response fields remain unchanged. The frontend stays on unversioned routes. Graph projection, job state,
safe source reading, and analysis are adapter concerns rather than Intelligence Kernel operations.

Legacy intelligence shapes remain:

- query: `{version, query, results}`
- context: `{version, symbol, depth, nodes, edges}`
- impact: `{version, symbol, depth, results}`
- diagnostics: `{version, total, matched, truncated, items, by_severity, by_code}`

## New versioned routes

```text
POST /api/v1/intelligence/query
POST /api/v1/intelligence/context
POST /api/v1/intelligence/impact
POST /api/v1/intelligence/diagnostics
POST /api/v1/intelligence/path
POST /api/v1/intelligence/context-package
```

The JSON body is the v1 request without transport-derived `operation`; the route supplies it. A body may
still include the same operation, but a mismatch is `invalid_request`. Responses use the v1 normalized
result/error envelope and `Content-Type: application/json; charset=utf-8`.

## Status mapping

| Kernel condition | HTTP status |
| --- | --- |
| Successful result, including no-match/not-connected/ambiguous | 200 |
| Invalid request/parameter/missing target | 400 |
| Unsupported contract major or graph schema | 409 |
| Graph not ready or identity mismatch | 409 |
| Graph integrity failure | 422 |
| Unexpected internal failure | 500 |

The normalized error code is unchanged by transport mapping. Existing unversioned errors retain their
historical `{error:{code,message}}` shape.

## Snapshot behavior

`DashboardState` publishes graph and kernel atomically. One request uses one snapshot for its full lifetime
and reports that snapshot revision. Re-analysis may replace the published snapshot only after successful
completion; a failed job retains the previous valid graph and kernel.

Request bodies remain under the existing 64 KiB cap. Source evidence probes reuse current containment
and file-type protections; v1 context packages do not include raw source text.
