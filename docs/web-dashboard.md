# Local Web Dashboard

The dashboard is a same-origin local application over the canonical MQL5 CodeGraph engine. It does
not upload source, require an account, or replace the deterministic JSON/CLI contracts.

## Start

```powershell
mql5-codegraph serve --root C:\work\Example-MQL5
```

Useful options:

- `--include-root <path>` adds an MQL5 include lookup root.
- `--graph <graph.json>` opens a saved graph; use `--root` when its metadata lacks a valid root.
- `--port 0` requests an available loopback port.
- `--no-browser` starts without opening the default browser.
- `--host` should remain `127.0.0.1` unless the operator explicitly accepts network exposure.

## Product workflow

1. Enter a source root and optional MetaTrader include root.
2. Analyze or re-index. A failed re-index retains the last valid graph.
3. Search for a symbol or inspect the repository projection.
4. Select nodes to view evidence, incoming/outgoing relationships, context, and upstream impact.
5. Filter diagnostics and open the exact source line in the protected viewer.

The browser receives at most 2,000 nodes per projection while the Python process retains the complete
canonical graph. This separates analysis scale from visualization scale.

## Security boundary

- The default listener is loopback-only and emits no permissive CORS headers.
- Request bodies are limited to 64 KiB.
- Source reads accept only `.mq5` and `.mqh` files contained under the active repository root.
- Source viewer files are capped at 2 MiB.
- Static responses include CSP, same-origin resource, referrer, and content-type protections.

## Frontend development

Run the Python dashboard API on port `8765`, then:

```powershell
cd web
npm run dev
```

The Vite development server proxies `/api` to the local Python server. Production builds are emitted
to `src/mql5_codegraph/web_static/` for the CLI server.
