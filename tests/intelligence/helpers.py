"""Deterministic graph and request builders used by intelligence tests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from mql5_codegraph.diagnostics import Diagnostic
from mql5_codegraph.graph import (
    CodeGraph,
    GraphEdge,
    GraphNode,
    SourceLocation,
    stable_id,
)


DEFAULT_BOUNDS: dict[str, int] = {
    "max_depth": 1,
    "max_items": 30,
    "max_paths": 3,
    "max_expansions": 10_000,
    "context_units": 100,
}


def make_node(
    name: str,
    *,
    kind: str = "function",
    qualified_name: str | None = None,
    node_id: str | None = None,
    location: SourceLocation | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> GraphNode:
    """Build a node whose identity is stable across test insertion orders."""

    qualified = qualified_name or name
    return GraphNode(
        id=node_id or stable_id("test-node", kind, qualified),
        kind=kind,
        name=name,
        qualified_name=qualified,
        location=location,
        attributes=dict(attributes or {}),
    )


def make_edge(
    source: GraphNode | str,
    target: GraphNode | str,
    *,
    relationship: str = "calls",
    origin: str = "extracted",
    confidence: float = 1.0,
    edge_id: str | None = None,
    location: SourceLocation | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> GraphEdge:
    """Build an explicit edge without depending on a graph's mutation order."""

    source_id = source.id if isinstance(source, GraphNode) else source
    target_id = target.id if isinstance(target, GraphNode) else target
    location_key = (
        f"{location.file}:{location.line}:{location.column}" if location else ""
    )
    return GraphEdge(
        id=edge_id
        or stable_id(
            "test-edge",
            source_id,
            relationship,
            target_id,
            origin,
            location_key,
        ),
        source=source_id,
        target=target_id,
        relationship=relationship,
        origin=origin,
        confidence=confidence,
        location=location,
        attributes=dict(attributes or {}),
    )


def build_graph(
    nodes: Iterable[GraphNode] = (),
    edges: Iterable[GraphEdge] = (),
    diagnostics: Iterable[Diagnostic] = (),
    *,
    metadata: Mapping[str, Any] | None = None,
) -> CodeGraph:
    """Build a canonical graph from explicit records in the supplied order."""

    graph = CodeGraph(
        {
            "source_fingerprint": "test-source-fingerprint",
            **dict(metadata or {}),
        }
    )
    for node in nodes:
        graph.add_node(node)
    for edge in edges:
        graph.edges.setdefault(edge.id, edge)
    for diagnostic in diagnostics:
        graph.add_diagnostic(diagnostic)
    return graph


def request_payload(
    operation: str,
    *targets: str,
    bounds: Mapping[str, int] | None = None,
    direction: str = "both",
    relationship_types: Iterable[str] = (),
    node_kinds: Iterable[str] = (),
    **overrides: Any,
) -> dict[str, Any]:
    """Build a complete normalized v1 request payload with stable ordering."""

    payload: dict[str, Any] = {
        "contract_version": "1.0.0",
        "operation": operation,
        "targets": [{"value": target, "kind": None} for target in targets],
        "direction": direction,
        "relationship_types": sorted(relationship_types),
        "node_kinds": sorted(node_kinds),
        "bounds": {**DEFAULT_BOUNDS, **dict(bounds or {})},
        "expected_source_fingerprint": None,
        "client_request_id": None,
    }
    payload.update(overrides)
    return payload
