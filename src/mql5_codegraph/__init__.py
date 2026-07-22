"""MQL5-aware static code graph indexing."""

from .graph import CodeGraph, GraphEdge, GraphNode, SourceLocation
from .indexer import analyze_repository

__all__ = ["CodeGraph", "GraphEdge", "GraphNode", "SourceLocation", "analyze_repository"]
__version__ = "0.2.0"
