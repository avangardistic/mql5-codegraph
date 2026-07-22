"""Repository discovery and end-to-end MQL5 graph construction."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Iterable

from .diagnostics import Diagnostic, DECODE_RECOVERY
from .graph import CodeGraph, SourceLocation
from .parser import parse_source
from .resolver import ParsedUnit, build_graph
from .runtime import enrich_runtime


DEFAULT_EXCLUDED_DIRECTORIES = {".git", ".gitnexus", "graphify-out", "build", "dist", "__pycache__"}


def discover_sources(root: Path, excluded: Iterable[str] = ()) -> list[Path]:
    excluded_names = DEFAULT_EXCLUDED_DIRECTORIES | set(excluded)
    return sorted(
        (path for path in root.rglob("*")
         if path.is_file() and path.suffix.lower() in {".mq5", ".mqh"}
         and not any(part in excluded_names for part in path.relative_to(root).parts)),
        key=lambda path: path.relative_to(root).as_posix().casefold(),
    )


def analyze_repository(
    root: str | Path, include_roots: Iterable[str | Path] = (), excluded: Iterable[str] = (),
) -> CodeGraph:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError(f"Analysis root is not a directory: {root_path}")
    include_paths = [Path(path).resolve() for path in include_roots]
    source_paths = discover_sources(root_path, excluded)
    digest = sha256()
    units: list[ParsedUnit] = []
    decode_diagnostics: list[Diagnostic] = []
    for path in source_paths:
        relative = path.relative_to(root_path).as_posix()
        data = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
            decode_diagnostics.append(Diagnostic(
                DECODE_RECOVERY, "warning", "Invalid UTF-8 bytes replaced during decoding",
                SourceLocation(relative, 1, 1),
            ))
        units.append(ParsedUnit(path.resolve(), relative, parse_source(text, relative)))
    graph, _ = build_graph(units, root_path, include_paths, digest.hexdigest())
    for diagnostic in decode_diagnostics:
        graph.add_diagnostic(diagnostic)
    enrich_runtime(graph)
    graph.metadata.update({
        "node_count": len(graph.nodes), "edge_count": len(graph.edges),
        "diagnostic_count": len(graph.diagnostics),
    })
    return graph
