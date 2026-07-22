# Data Model: Local Web Dashboard

## DashboardState

- `graph`: current immutable CodeGraph reference or null
- `root`: resolved active repository root or null
- `graph_version`: monotonically increasing integer
- `active_job_id`: current running job or null
- `jobs`: bounded recent job records
- `last_error`: latest public error message or null

State transitions: empty -> analyzing -> ready; ready -> analyzing -> ready/error. A failed re-index keeps
the previous valid graph available.

## AnalysisJob

- `id`: random opaque identifier
- `status`: queued, running, completed, failed
- `root`, `include_roots`: requested paths
- `started_at`, `finished_at`: UTC timestamps
- `summary`: file/node/edge/diagnostic counts on success
- `error`: sanitized failure message on failure

Only one queued/running job is permitted. Completed history is bounded.

## VisualizationGraph

- `version`: active graph version
- `nodes`, `edges`: canonical graph dictionaries transformed for the web client
- `total_nodes`, `total_edges`: canonical counts
- `visible_nodes`, `visible_edges`: projection counts
- `truncated`: whether limits excluded matches
- `filters`: applied kinds, relationships, query, and limit

## SourceEvidence

- `file`: normalized repository-relative path
- `content`: decoded text subject to size limit
- `line_count`: total lines
- `highlight_line`: optional validated one-based line
- `language`: `mql5`
