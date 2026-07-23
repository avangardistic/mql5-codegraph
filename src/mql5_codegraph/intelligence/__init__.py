"""Backend-neutral, read-only intelligence over canonical graph snapshots.

The package owns versioned intelligence contracts and deterministic graph
operations. CLI, Web, and future protocol adapters project those operations
without adding analysis semantics of their own.

Only the versioned v1 contract types and kernel facade are exported here.
"""

from .errors import IntelligenceError
from .index import GraphIndex
from .kernel import IntelligenceKernel
from .matching import resolve_target
from .models import (
    CONTRACT_VERSION,
    CandidateMatch,
    Completion,
    ContextItem,
    ContextPackage,
    DiagnosticResult,
    DirectedPath,
    EvidenceReference,
    GraphIdentity,
    IntelligenceBounds,
    IntelligenceRequest,
    IntelligenceResult,
    NodeSummary,
    OmissionSummary,
    PathHop,
    RelationshipResult,
    SymbolSelector,
    TargetResolution,
)

__all__ = (
    "CONTRACT_VERSION",
    "CandidateMatch",
    "Completion",
    "ContextItem",
    "ContextPackage",
    "DiagnosticResult",
    "DirectedPath",
    "EvidenceReference",
    "GraphIdentity",
    "GraphIndex",
    "IntelligenceBounds",
    "IntelligenceError",
    "IntelligenceKernel",
    "IntelligenceRequest",
    "IntelligenceResult",
    "NodeSummary",
    "OmissionSummary",
    "PathHop",
    "RelationshipResult",
    "SymbolSelector",
    "TargetResolution",
    "resolve_target",
)
