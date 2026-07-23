# ADR-0002: Local dashboard security boundary

- Status: Accepted
- Date: 2026-07-23
- Owners: Project maintainers

## Context

The dashboard uses Python's local HTTP server without authentication. A two-second socket timeout bounded
idle reads, but a client sending bytes just before each timeout could retain every request-thread slot.
The CLI also accepted non-loopback bind addresses, and a saved graph's metadata could implicitly select a
filesystem root for source viewing. Those behaviors exceeded the intended offline single-user boundary.

## Decision

Keep the dashboard an explicitly loopback-only adapter:

- reject non-loopback bind addresses;
- require request `Host` authorities to be loopback and on the active server port when one is supplied;
- reject browser `Origin` values that are not HTTP loopback origins on the active server port;
- retain the two-second idle read timeout and add a ten-second absolute deadline covering the request line,
  headers, and declared body;
- retain the 64 KiB body limit and finite request-thread budget;
- never infer source-viewer authority from saved graph metadata; an explicit active root is required.

Remote, authenticated, or multi-user access is a different adapter boundary. It must be designed explicitly
or placed behind a trusted authenticated proxy instead of weakening this server's loopback invariant.

## Consequences

- Positive: slow-drip clients cannot retain request slots indefinitely.
- Positive: DNS rebinding and accidental LAN exposure do not cross the supported dashboard boundary.
- Positive: loading an untrusted graph cannot redirect the source viewer to an arbitrary metadata path.
- Cost: existing uses of `--host 0.0.0.0` or a LAN address now fail fast.
- Cost: loading a graph without `--root` keeps graph intelligence available but disables source viewing.
- Risk: completed analysis work has no general wall-clock deadline; analysis resource controls remain a
  separate kernel/indexer concern.

## Guardrails

- Loopback, origin, deadline, and source-root behavior must have executable regression coverage.
- A proposal to expose the dashboard remotely requires a new or superseding ADR with authentication,
  authorization, origin, transport, and deployment controls.
- Parser and graph-expansion work budgets must be decided before hosted untrusted-repository ingestion.
