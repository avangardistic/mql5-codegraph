import contextlib
from http.client import HTTPConnection
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest import TestCase

from mql5_codegraph.cli import run
from mql5_codegraph.diagnostics import Diagnostic
from mql5_codegraph.graph import SourceLocation
from mql5_codegraph.intelligence.context import assemble_context_package
from mql5_codegraph.intelligence.errors import IntelligenceError
from mql5_codegraph.intelligence.index import GraphIndex
from mql5_codegraph.intelligence.kernel import IntelligenceKernel
from mql5_codegraph.intelligence.models import (
    IntelligenceBounds,
    IntelligenceRequest,
    SymbolSelector,
)
from mql5_codegraph.web.api import DashboardApi
from mql5_codegraph.web.server import create_server
from mql5_codegraph.web.state import DashboardState

from .helpers import build_graph, make_edge, make_node


class ContextPackageTests(TestCase):
    def test_ranking_is_deterministic_and_relationship_groups_are_atomic(self) -> None:
        target = make_node(
            "Target",
            node_id="node:target",
            location=SourceLocation("Target.mq5", 1, 1),
        )
        direct = make_node("Direct", node_id="node:direct")
        second = make_node("Second", node_id="node:second")
        direct_edge = make_edge(
            target,
            direct,
            edge_id="edge:direct",
            origin="resolved",
            confidence=0.9,
            location=SourceLocation("Target.mq5", 2, 3),
        )
        second_edge = make_edge(
            direct,
            second,
            edge_id="edge:second",
            origin="inferred",
            confidence=0.4,
            location=SourceLocation("Other.mqh", 4, 5),
        )
        local = Diagnostic(
            "LOCAL001",
            "warning",
            "Local warning",
            SourceLocation("Target.mq5", 3, 1),
        )
        bounds = IntelligenceBounds(
            max_depth=2,
            max_expansions=100,
            context_units=10,
        )

        first = assemble_context_package(
            GraphIndex(
                build_graph(
                    [target, direct, second],
                    [direct_edge, second_edge],
                    [local],
                )
            ),
            [target.id],
            bounds,
        )
        second_order = assemble_context_package(
            GraphIndex(
                build_graph(
                    [second, direct, target],
                    [second_edge, direct_edge],
                    [local],
                )
            ),
            [target.id],
            bounds,
        )

        self.assertEqual(first.package.to_dict(), second_order.package.to_dict())
        categories = tuple(item.category for item in first.package.items)
        self.assertEqual(
            (
                "target",
                "node",
                "relationship",
                "diagnostic",
                "node",
                "relationship",
            ),
            categories,
        )
        selected_nodes = {
            item.subject_id
            for item in first.package.items
            if item.category in {"target", "node"}
        }
        for item in first.package.items:
            if item.category == "relationship":
                self.assertIn(item.summary["source"], selected_nodes)
                self.assertIn(item.summary["target"], selected_nodes)
                self.assertIsNotNone(item.evidence)
        self.assertEqual(len(first.package.items), first.package.budget_used)
        self.assertLessEqual(first.package.budget_used, bounds.context_units)

    def test_tiny_budget_never_emits_a_partial_relationship_group(self) -> None:
        target = make_node("Target", node_id="node:target")
        neighbor = make_node("Neighbor", node_id="node:neighbor")
        edge = make_edge(target, neighbor, edge_id="edge:target-neighbor")
        result = assemble_context_package(
            GraphIndex(build_graph([neighbor, target], [edge])),
            [target.id],
            IntelligenceBounds(
                max_depth=1,
                max_expansions=100,
                context_units=2,
            ),
        )

        self.assertEqual(("target",), tuple(item.category for item in result.package.items))
        self.assertEqual(1, result.package.budget_used)
        self.assertEqual("context_budget", result.completion.reason)
        self.assertTrue(result.completion.truncated)
        self.assertEqual(
            {"nodes": 1, "relationships": 1},
            {item.category: item.count for item in result.package.omissions},
        )

    def test_ambiguous_targets_are_retained_or_disclosed_as_omitted(self) -> None:
        alpha = make_node(
            "Target",
            qualified_name="Alpha.Target",
            node_id="node:alpha-target",
        )
        beta = make_node(
            "Target",
            qualified_name="Beta.Target",
            node_id="node:beta-target",
        )
        index = GraphIndex(build_graph([beta, alpha]))

        complete = assemble_context_package(
            index,
            [beta.id, alpha.id],
            IntelligenceBounds(context_units=2),
        )
        constrained = assemble_context_package(
            index,
            [beta.id, alpha.id],
            IntelligenceBounds(context_units=1),
        )

        self.assertEqual(
            (alpha.id, beta.id),
            tuple(item.subject_id for item in complete.package.items),
        )
        self.assertEqual((), complete.package.omissions)
        self.assertEqual((alpha.id,), tuple(item.subject_id for item in constrained.package.items))
        self.assertEqual(
            {"ambiguity_alternatives": 1, "nodes": 1},
            {item.category: item.count for item in constrained.package.omissions},
        )

    def test_evidence_states_include_locationless_stale_unavailable_and_unknown(self) -> None:
        target = make_node("Target", node_id="node:target")
        neighbors = [
            make_node(name, node_id=f"node:{name.casefold()}")
            for name in ("Locationless", "Stale", "Unavailable", "Unknown")
        ]
        edges = [
            make_edge(
                target,
                node,
                edge_id=f"edge:{node.name.casefold()}",
                location=(
                    None
                    if node.name == "Locationless"
                    else SourceLocation(f"{node.name}.mqh", 1, 1)
                ),
            )
            for node in neighbors
        ]
        states = {
            "edge:stale": ("stale", "fingerprint_mismatch"),
            "edge:unavailable": ("unavailable", "file_missing"),
            "edge:unknown": ("unknown", "probe_inconclusive"),
        }
        result = assemble_context_package(
            GraphIndex(build_graph([target, *neighbors], edges)),
            [target.id],
            IntelligenceBounds(max_depth=1, context_units=20),
            evidence_probe=lambda edge: states.get(edge.id, ("available", None)),
        )
        evidence = {
            item.subject_id: item.evidence
            for item in result.package.items
            if item.category == "relationship"
        }

        self.assertEqual("unknown", evidence["edge:locationless"].state)
        self.assertEqual(
            "location_missing",
            evidence["edge:locationless"].state_reason,
        )
        self.assertEqual("stale", evidence["edge:stale"].state)
        self.assertEqual("unavailable", evidence["edge:unavailable"].state)
        self.assertEqual("unknown", evidence["edge:unknown"].state)

    def test_kernel_dispatch_serializes_context_package_and_preserves_ambiguity(self) -> None:
        alpha = make_node(
            "Target",
            qualified_name="Alpha.Target",
            node_id="node:alpha-target",
        )
        beta = make_node(
            "Target",
            qualified_name="Beta.Target",
            node_id="node:beta-target",
        )
        graph = build_graph([beta, alpha])
        before = graph.to_json()
        result = IntelligenceKernel(graph).execute(
            IntelligenceRequest(
                operation="context_package",
                targets=(SymbolSelector("Target"),),
                direction="both",
                bounds=IntelligenceBounds(
                    max_depth=2,
                    max_expansions=100,
                    context_units=2,
                ),
            )
        )

        self.assertEqual("ambiguous", result.resolution[0].status)
        self.assertIsNotNone(result.context_package)
        self.assertEqual(2, result.context_package.budget_used)
        self.assertEqual(
            (alpha.id, beta.id),
            tuple(item.subject_id for item in result.context_package.items),
        )
        self.assertEqual(result.to_dict(), json.loads(result.to_json()))
        self.assertEqual(before, graph.to_json())

    def test_cli_and_http_project_context_package_defaults_and_errors(self) -> None:
        target = make_node("Target", node_id="node:target")
        graph = build_graph([target])
        state = DashboardState()
        state.load_graph(graph, Path.cwd())
        api = DashboardApi(state)
        payload = api.intelligence(
            "context_package",
            {
                "contract_version": "1.0.0",
                "targets": [{"value": target.id, "kind": None}],
            },
        )
        self.assertEqual("both", payload["request"]["direction"])
        self.assertEqual(2, payload["limits_applied"]["max_depth"])
        self.assertEqual(100, payload["limits_applied"]["context_units"])

        with self.assertRaises(IntelligenceError) as malformed:
            api.intelligence(
                "context_package",
                {
                    "contract_version": "1.0.0",
                    "targets": [{"value": target.id, "kind": None}],
                    "bounds": [],
                },
            )
        self.assertEqual("invalid_parameter", malformed.exception.code)
        self.assertEqual("bounds", malformed.exception.field)

        with TemporaryDirectory() as directory:
            graph_path = Path(directory) / "graph.json"
            graph.save(graph_path)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = run(
                    [
                        "intelligence",
                        "context-package",
                        str(graph_path),
                        target.id,
                        "--context-units",
                        "1",
                        "--json",
                    ]
                )
            self.assertEqual(0, exit_code)
            self.assertEqual("", stderr.getvalue())
            cli = json.loads(stdout.getvalue())
            self.assertEqual("context_package", cli["operation"])
            self.assertEqual(1, cli["limits_applied"]["context_units"])

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = run(
                    [
                        "intelligence",
                        "context-package",
                        str(graph_path),
                        target.id,
                        "--context-units",
                        "0",
                        "--json",
                    ]
                )
            self.assertEqual(1, exit_code)
            self.assertEqual("", stdout.getvalue())
            error = json.loads(stderr.getvalue())["error"]
            self.assertEqual("invalid_parameter", error["code"])
            self.assertEqual("bounds.context_units", error["field"])

    def test_us3_acceptance_slice_is_equivalent_across_direct_cli_and_http(self) -> None:
        target = make_node("Target", node_id="node:target")
        preferred = make_node("Preferred", node_id="node:preferred")
        omitted = make_node("Omitted", node_id="node:omitted")
        graph = build_graph(
            [omitted, preferred, target],
            [
                make_edge(
                    target,
                    preferred,
                    edge_id="edge:preferred",
                    origin="resolved",
                    confidence=0.9,
                    location=SourceLocation("Target.mq5", 2, 1),
                ),
                make_edge(
                    target,
                    omitted,
                    edge_id="edge:omitted",
                    origin="inferred",
                    confidence=0.4,
                    location=SourceLocation("Target.mq5", 3, 1),
                ),
            ],
        )
        request = {
            "contract_version": "1.0.0",
            "operation": "context_package",
            "targets": [{"value": target.id, "kind": None}],
            "direction": "both",
            "relationship_types": [],
            "node_kinds": [],
            "bounds": {
                "max_depth": 2,
                "max_items": 30,
                "max_paths": 3,
                "max_expansions": 100,
                "context_units": 4,
            },
            "expected_source_fingerprint": None,
            "client_request_id": None,
        }
        direct = IntelligenceKernel(graph).execute(request).to_dict()
        self.assertEqual("context_budget", direct["completion"]["reason"])
        self.assertLessEqual(
            direct["context_package"]["budget_used"],
            request["bounds"]["context_units"],
        )
        self.assertEqual(
            {"nodes": 1, "relationships": 1},
            {
                item["category"]: item["count"]
                for item in direct["context_package"]["omissions"]
            },
        )

        with TemporaryDirectory() as directory:
            graph_path = Path(directory) / "graph.json"
            graph.save(graph_path)
            cli_payloads = []
            for _ in range(2):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    self.assertEqual(
                        0,
                        run(
                            [
                                "intelligence",
                                "context-package",
                                str(graph_path),
                                target.id,
                                "--max-depth",
                                "2",
                                "--max-expansions",
                                "100",
                                "--context-units",
                                "4",
                                "--json",
                            ]
                        ),
                    )
                cli_payloads.append(json.loads(stdout.getvalue()))
            self.assertEqual(direct, cli_payloads[0])
            self.assertEqual(cli_payloads[0], cli_payloads[1])

            state = DashboardState()
            state.load_graph(graph, Path(directory))
            server = create_server(state, port=0)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                http_payloads = []
                body_value = {key: value for key, value in request.items() if key != "operation"}
                body = json.dumps(body_value).encode("utf-8")
                for _ in range(2):
                    connection = HTTPConnection(
                        "127.0.0.1",
                        server.server_port,
                        timeout=3,
                    )
                    connection.request(
                        "POST",
                        "/api/v1/intelligence/context-package",
                        body=body,
                        headers={
                            "Content-Type": "application/json",
                            "Content-Length": str(len(body)),
                        },
                    )
                    response = connection.getresponse()
                    self.assertEqual(200, response.status)
                    self.assertEqual(
                        "application/json; charset=utf-8",
                        response.getheader("Content-Type"),
                    )
                    payload = json.loads(response.read())
                    payload["graph_identity"]["snapshot_revision"] = None
                    http_payloads.append(payload)
                    connection.close()
                self.assertEqual(direct, http_payloads[0])
                self.assertEqual(http_payloads[0], http_payloads[1])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
