import json
from unittest import TestCase

from mql5_codegraph.intelligence.errors import IntelligenceError
from mql5_codegraph.intelligence.kernel import IntelligenceKernel
from mql5_codegraph.intelligence.models import (
    Completion,
    EvidenceReference,
    GraphIdentity,
    IntelligenceBounds,
    IntelligenceRequest,
    IntelligenceResult,
    SymbolSelector,
)
from tests.intelligence.helpers import build_graph, make_node


class IntelligenceModelTests(TestCase):
    def test_bounds_validate_every_contract_limit(self) -> None:
        for field, invalid in (
            ("max_depth", -1),
            ("max_depth", 6),
            ("max_items", 0),
            ("max_items", 2001),
            ("max_paths", 0),
            ("max_paths", 21),
            ("max_expansions", 0),
            ("max_expansions", 100_001),
            ("context_units", 0),
            ("context_units", 10_001),
        ):
            with self.subTest(field=field, invalid=invalid):
                values = {
                    "max_depth": 1,
                    "max_items": 30,
                    "max_paths": 3,
                    "max_expansions": 10_000,
                    "context_units": 100,
                    field: invalid,
                }
                with self.assertRaisesRegex(ValueError, field):
                    IntelligenceBounds(**values)

    def test_request_normalizes_order_and_validates_version(self) -> None:
        request = IntelligenceRequest(
            operation="query",
            targets=(SymbolSelector("OnTick"),),
            relationship_types=("runtime_dispatches", "calls", "calls"),
            node_kinds=("method", "function"),
        )
        self.assertEqual(("calls", "runtime_dispatches"), request.relationship_types)
        self.assertEqual(("function", "method"), request.node_kinds)
        self.assertEqual("1.0.0", request.to_dict()["contract_version"])
        with self.assertRaisesRegex(ValueError, "contract_version"):
            IntelligenceRequest(operation="query", contract_version="2.0.0")
        with self.assertRaisesRegex(ValueError, "operation"):
            IntelligenceRequest(operation="unknown")

    def test_result_has_complete_stable_schema_and_canonical_json(self) -> None:
        request = IntelligenceRequest(
            operation="query", targets=(SymbolSelector("OnTick"),)
        )
        result = IntelligenceResult(
            operation="query",
            graph_identity=GraphIdentity("1.0.0", "fingerprint", 2),
            request=request,
            completion=Completion.complete(),
        )
        expected_keys = {
            "contract_version",
            "operation",
            "graph_identity",
            "request",
            "resolution",
            "nodes",
            "relationships",
            "paths",
            "context_package",
            "diagnostics",
            "limits_applied",
            "completion",
        }
        self.assertEqual(expected_keys, set(result.to_dict()))
        self.assertEqual(result.to_dict(), json.loads(result.to_json()))
        self.assertEqual(result.to_json(), result.to_json())

    def test_evidence_is_immutable_and_serializes_missing_location(self) -> None:
        evidence = EvidenceReference(
            subject_id="edge:1",
            origin="runtime",
            confidence=0.75,
            location=None,
            state="unknown",
            state_reason="probe_not_configured",
        )
        self.assertEqual(None, evidence.to_dict()["location"])
        with self.assertRaisesRegex(ValueError, "confidence"):
            EvidenceReference("edge:1", "extracted", 1.1)
        with self.assertRaises((AttributeError, TypeError)):
            evidence.state = "available"

    def test_errors_have_stable_machine_readable_envelopes(self) -> None:
        error = IntelligenceError.invalid_parameter(
            "bounds.max_depth", "must be between 0 and 5"
        )
        self.assertEqual("invalid_parameter", error.code)
        self.assertEqual("request", error.category)
        self.assertEqual("bounds.max_depth", error.field)
        self.assertEqual(
            {"error": error.to_dict()},
            json.loads(error.to_json()),
        )

    def test_kernel_negotiates_snapshot_identity_and_dispatch_errors(self) -> None:
        graph = build_graph([make_node("OnTick")])
        kernel = IntelligenceKernel(graph, snapshot_revision=7)
        self.assertEqual(7, kernel.graph_identity.snapshot_revision)
        self.assertEqual(
            "test-source-fingerprint", kernel.graph_identity.source_fingerprint
        )
        with self.assertRaises(IntelligenceError) as mismatch:
            kernel.execute(
                IntelligenceRequest(
                    operation="query",
                    expected_source_fingerprint="different",
                )
            )
        self.assertEqual("graph_identity_mismatch", mismatch.exception.code)
        with self.assertRaises(IntelligenceError) as missing_target:
            kernel.execute(IntelligenceRequest(operation="query"))
        self.assertEqual("missing_target", missing_target.exception.code)
        with self.assertRaises(IntelligenceError) as context_missing_target:
            kernel.execute(IntelligenceRequest(operation="context_package"))
        self.assertEqual(
            "missing_target",
            context_missing_target.exception.code,
        )
