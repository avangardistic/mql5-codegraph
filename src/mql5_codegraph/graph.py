"""Canonical, backend-neutral graph model and traversal helpers."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Iterable

from .diagnostics import Diagnostic

SCHEMA_VERSION = "1.0.0"


def stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    digest = sha1(payload.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}:{digest}"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    file: str
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"file": self.file, "line": self.line, "column": self.column}
        if self.end_line is not None:
            value["end_line"] = self.end_line
        if self.end_column is not None:
            value["end_column"] = self.end_column
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SourceLocation":
        return cls(**value)


@dataclass(frozen=True, slots=True)
class GraphNode:
    id: str
    kind: str
    name: str
    qualified_name: str
    location: SourceLocation | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "attributes": dict(sorted(self.attributes.items())),
        }
        if self.location is not None:
            value["location"] = self.location.to_dict()
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GraphNode":
        location = value.get("location")
        return cls(
            id=value["id"],
            kind=value["kind"],
            name=value["name"],
            qualified_name=value["qualified_name"],
            location=SourceLocation.from_dict(location) if location else None,
            attributes=value.get("attributes", {}),
        )


@dataclass(frozen=True, slots=True)
class GraphEdge:
    id: str
    source: str
    target: str
    relationship: str
    origin: str
    confidence: float
    location: SourceLocation | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "relationship": self.relationship,
            "origin": self.origin,
            "confidence": self.confidence,
            "attributes": dict(sorted(self.attributes.items())),
        }
        if self.location is not None:
            value["location"] = self.location.to_dict()
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GraphEdge":
        location = value.get("location")
        return cls(
            id=value["id"], source=value["source"], target=value["target"],
            relationship=value["relationship"], origin=value["origin"],
            confidence=float(value["confidence"]),
            location=SourceLocation.from_dict(location) if location else None,
            attributes=value.get("attributes", {}),
        )


class CodeGraph:
    def __init__(self, metadata: dict[str, Any] | None = None) -> None:
        self.schema_version = SCHEMA_VERSION
        self.metadata = metadata or {}
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[str, GraphEdge] = {}
        self.diagnostics: list[Diagnostic] = []

    def add_node(self, node: GraphNode) -> GraphNode:
        self.nodes.setdefault(node.id, node)
        return self.nodes[node.id]

    def add_edge(
        self, source: str, target: str, relationship: str, origin: str,
        confidence: float, location: SourceLocation | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> GraphEdge:
        location_key = ""
        if location:
            location_key = f"{location.file}:{location.line}:{location.column}"
        edge_id = stable_id("edge", source, relationship, target, origin, location_key)
        edge = GraphEdge(edge_id, source, target, relationship, origin, confidence,
                         location, attributes or {})
        self.edges.setdefault(edge.id, edge)
        return self.edges[edge.id]

    def add_diagnostic(self, diagnostic: Diagnostic) -> None:
        self.diagnostics.append(diagnostic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "metadata": dict(sorted(self.metadata.items())),
            "nodes": [self.nodes[key].to_dict() for key in sorted(self.nodes)],
            "edges": [self.edges[key].to_dict() for key in sorted(self.edges)],
            "diagnostics": [
                item.to_dict() for item in sorted(
                    self.diagnostics,
                    key=lambda d: (d.severity, d.code, d.location.file if d.location else "",
                                   d.location.line if d.location else 0, d.message),
                )
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(self.to_json(), encoding="utf-8", newline="\n")
        temporary.replace(target)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CodeGraph":
        if value.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"Unsupported graph schema: {value.get('schema_version')!r}")
        graph = cls(value.get("metadata", {}))
        for node in value.get("nodes", []):
            graph.add_node(GraphNode.from_dict(node))
        for edge in value.get("edges", []):
            parsed = GraphEdge.from_dict(edge)
            graph.edges[parsed.id] = parsed
        graph.diagnostics = [Diagnostic.from_dict(item) for item in value.get("diagnostics", [])]
        return graph

    @classmethod
    def load(cls, path: str | Path) -> "CodeGraph":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def find_nodes(self, text: str, kind: str | None = None) -> list[GraphNode]:
        needle = text.casefold()
        return sorted(
            (node for node in self.nodes.values()
             if (kind is None or node.kind == kind)
             and (needle in node.name.casefold() or needle in node.qualified_name.casefold())),
            key=lambda node: (node.qualified_name.casefold(), node.id),
        )

    def neighborhood(self, seeds: Iterable[str], depth: int = 1) -> dict[str, Any]:
        seen = set(seeds)
        queue = deque((seed, 0) for seed in seen)
        selected_edges: dict[str, GraphEdge] = {}
        incident: dict[str, list[GraphEdge]] = {}
        for edge in self.edges.values():
            incident.setdefault(edge.source, []).append(edge)
            incident.setdefault(edge.target, []).append(edge)
        while queue:
            current, distance = queue.popleft()
            if distance >= depth:
                continue
            for edge in incident.get(current, []):
                selected_edges[edge.id] = edge
                other = edge.target if edge.source == current else edge.source
                if other not in seen:
                    seen.add(other)
                    queue.append((other, distance + 1))
        return {
            "nodes": [self.nodes[node_id].to_dict() for node_id in sorted(seen) if node_id in self.nodes],
            "edges": [selected_edges[edge_id].to_dict() for edge_id in sorted(selected_edges)],
        }

    def upstream_impact(self, seeds: Iterable[str], depth: int = 3) -> list[dict[str, Any]]:
        allowed = {"calls", "includes", "defines", "runtime_dispatches", "may_trigger_event"}
        reverse: dict[str, list[GraphEdge]] = {}
        for edge in self.edges.values():
            if edge.relationship in allowed:
                reverse.setdefault(edge.target, []).append(edge)
        queue = deque((seed, 0, []) for seed in seeds)
        best: dict[str, tuple[int, list[str]]] = {seed: (0, []) for seed in seeds}
        while queue:
            current, distance, path = queue.popleft()
            if distance >= depth:
                continue
            for edge in sorted(reverse.get(current, []), key=lambda item: item.id):
                candidate = distance + 1
                new_path = path + [edge.id]
                if edge.source not in best or candidate < best[edge.source][0]:
                    best[edge.source] = (candidate, new_path)
                    queue.append((edge.source, candidate, new_path))
        return [
            {"node": self.nodes[node_id].to_dict(), "distance": distance, "edge_path": path}
            for node_id, (distance, path) in sorted(best.items(), key=lambda item: (item[1][0], item[0]))
            if distance > 0 and node_id in self.nodes
        ]
