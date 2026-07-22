# CLI Contract

All commands return exit code `0` on success and non-zero on invalid arguments, unreadable input, or
corrupt index data. `--json` output is written to stdout; diagnostics and progress go to stderr.

## analyze

`mql5-codegraph analyze <root> --output <graph.json> [--include-root <path>]...`

Discovers MQL5 files, builds the canonical graph, writes deterministic JSON, and prints a summary.

## status

`mql5-codegraph status <graph.json> [--json]`

Reports schema version, file count, node/edge counts, diagnostic counts, and source fingerprint.

## query

`mql5-codegraph query <graph.json> <text> [--kind <kind>] [--json]`

Returns case-insensitive name and qualified-name matches in deterministic order.

## context

`mql5-codegraph context <graph.json> <symbol> [--depth <n>] [--json]`

Returns matching symbol nodes and incident relationships up to the bounded depth.

## impact

`mql5-codegraph impact <graph.json> <symbol> [--depth <n>] [--json]`

Traverses reverse `calls`, `includes`, and `defines` relationships and reports affected nodes with
distance and path evidence.

## export

`mql5-codegraph export <graph.json> --format graphml --output <graph.graphml>`

Exports through a backend adapter without changing canonical identifiers.
