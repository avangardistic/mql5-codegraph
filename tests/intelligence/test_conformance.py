import contextlib
from http.client import HTTPConnection
import io
import json
from pathlib import Path
import random
from tempfile import TemporaryDirectory
from threading import Thread
from unittest import TestCase

from mql5_codegraph.cli import run
from mql5_codegraph.diagnostics import Diagnostic
from mql5_codegraph.graph import SourceLocation
from mql5_codegraph.intelligence import (
    IntelligenceBounds,
    IntelligenceKernel,
    IntelligenceRequest,
    SymbolSelector,
)
from mql5_codegraph.web.server import create_server
from mql5_codegraph.web.state import DashboardState
from tools.benchmark_intelligence import run_benchmark

from .helpers import build_graph, make_edge, make_node


class IntelligenceConformanceTests(TestCase):
    def test_reduced_benchmark_validates_without_enforcing_wall_clock(self) -> None:
        report = run_benchmark(
            node_count=200,
            request_count=24,
            warmups=4,
            enforce_timing=False,
        )

        self.assertEqual({"nodes": 200, "edges": 800, "diagnostics": 4}, report["graph"])
        self.assertEqual(24, report["requests"])
        self.assertEqual(24, report["validation"]["responses"])
        self.assertTrue(report["validation"]["graph_unchanged"])
        self.assertFalse(report["timing_enforced"])
        self.assertEqual(
            {"context", "context_package", "path", "query"},
            set(report["operations"]),
        )
        self.assertTrue(
            all(item["count"] == 6 for item in report["operations"].values())
        )

    def test_all_normalized_operations_are_stable_over_100_randomized_builds(self) -> None:
        caller = make_node("Caller", node_id="node:caller")
        target = make_node("Target", node_id="node:target")
        second = make_node("Second", node_id="node:second")
        edges = [
            make_edge(
                caller,
                target,
                edge_id="edge:caller-target",
                origin="resolved",
                confidence=0.9,
                location=SourceLocation("EA.mq5", 2, 1),
            ),
            make_edge(
                target,
                second,
                edge_id="edge:target-second",
                origin="inferred",
                confidence=0.5,
                location=SourceLocation("EA.mq5", 3, 1),
            ),
        ]
        diagnostics = [
            Diagnostic(
                "TEST001",
                "warning",
                "Synthetic warning",
                SourceLocation("EA.mq5", 4, 1),
            )
        ]
        requests = (
            IntelligenceRequest(
                operation="query",
                targets=(SymbolSelector("Target"),),
            ),
            IntelligenceRequest(
                operation="context",
                targets=(SymbolSelector("Target"),),
                direction="both",
                bounds=IntelligenceBounds(max_depth=2, max_items=30),
            ),
            IntelligenceRequest(
                operation="impact",
                targets=(SymbolSelector("Target"),),
                direction="incoming",
                bounds=IntelligenceBounds(max_depth=3, max_items=30),
            ),
            IntelligenceRequest(operation="diagnostics"),
            IntelligenceRequest(
                operation="path",
                targets=(SymbolSelector("Caller"), SymbolSelector("Second")),
                direction="outgoing",
                bounds=IntelligenceBounds(
                    max_depth=3,
                    max_paths=3,
                    max_expansions=100,
                ),
            ),
            IntelligenceRequest(
                operation="context_package",
                targets=(SymbolSelector("Target"),),
                direction="both",
                bounds=IntelligenceBounds(
                    max_depth=2,
                    max_expansions=100,
                    context_units=20,
                ),
            ),
        )
        expected = tuple(
            IntelligenceKernel(
                build_graph([caller, target, second], edges, diagnostics)
            ).execute(request).to_json()
            for request in requests
        )

        for iteration in range(100):
            nodes = [caller, target, second]
            shuffled_edges = list(edges)
            shuffled_diagnostics = list(diagnostics)
            generator = random.Random(iteration)
            generator.shuffle(nodes)
            generator.shuffle(shuffled_edges)
            generator.shuffle(shuffled_diagnostics)
            graph = build_graph(nodes, shuffled_edges, shuffled_diagnostics)
            before = graph.to_json()
            actual = tuple(
                IntelligenceKernel(graph).execute(request).to_json()
                for request in requests
            )
            with self.subTest(iteration=iteration):
                self.assertEqual(expected, actual)
                self.assertEqual(before, graph.to_json())

    def test_empty_and_missing_metadata_graphs_return_normalized_results(self) -> None:
        graph = build_graph(metadata={"source_fingerprint": None})
        before = graph.to_json()
        result = IntelligenceKernel(graph).execute(
            IntelligenceRequest(
                operation="query",
                targets=(SymbolSelector("missing"),),
            )
        )
        self.assertEqual("no_match", result.completion.reason)
        self.assertIsNone(result.graph_identity.source_fingerprint)
        self.assertEqual(before, graph.to_json())

    def test_query_and_diagnostics_item_bounds_report_truncation(self) -> None:
        alpha = make_node("Alpha")
        beta = make_node("Alphabet")
        graph = build_graph(
            [beta, alpha],
            diagnostics=(
                Diagnostic("A", "warning", "one"),
                Diagnostic("B", "warning", "two"),
            ),
        )
        kernel = IntelligenceKernel(graph)
        query = kernel.execute(
            IntelligenceRequest(
                operation="query",
                targets=(SymbolSelector("Alph"),),
                bounds=IntelligenceBounds(max_items=1),
            )
        )
        diagnostics = kernel.execute(
            IntelligenceRequest(
                operation="diagnostics",
                bounds=IntelligenceBounds(max_items=1),
            )
        )
        self.assertEqual("max_items", query.completion.reason)
        self.assertEqual("max_items", diagnostics.completion.reason)

    def test_direct_cli_and_http_contracts_share_the_same_shape(self) -> None:
        node = make_node("OnTick", location=SourceLocation("EA.mq5", 1, 1))
        graph = build_graph([node])
        direct = IntelligenceKernel(graph).execute(
            IntelligenceRequest(
                operation="query",
                targets=(SymbolSelector("OnTick"),),
            )
        ).to_dict()
        with TemporaryDirectory() as directory:
            graph_path = Path(directory) / "graph.json"
            graph.save(graph_path)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = run(
                    [
                        "intelligence",
                        "query",
                        str(graph_path),
                        "OnTick",
                        "--contract-version",
                        "1",
                        "--json",
                    ]
                )
        self.assertEqual(0, exit_code)
        cli = json.loads(stdout.getvalue())
        self.assertEqual(direct, cli)

        state = DashboardState()
        state.load_graph(graph, Path.cwd())
        server = create_server(state, port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = HTTPConnection(
                "127.0.0.1", server.server_port, timeout=3
            )
            body = json.dumps(direct["request"]).encode("utf-8")
            connection.request(
                "POST",
                "/api/v1/intelligence/query",
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "Content-Length": str(len(body)),
                },
            )
            response = connection.getresponse()
            http = json.loads(response.read())
            self.assertEqual(200, response.status)
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        http["graph_identity"]["snapshot_revision"] = None
        self.assertEqual(direct, http)

    def test_all_us1_operations_conform_across_direct_cli_and_http(self) -> None:
        caller = make_node("Caller")
        target = make_node("Target")
        edge = make_edge(
            caller,
            target,
            location=SourceLocation("EA.mq5", 3, 2),
        )
        graph = build_graph(
            [target, caller],
            [edge],
            [Diagnostic("TEST001", "warning", "synthetic")],
        )
        vectors = (
            (
                "query",
                IntelligenceRequest(
                    operation="query",
                    targets=(SymbolSelector("Caller"),),
                    bounds=IntelligenceBounds(max_depth=1, max_items=30),
                ),
                ["query", "Caller"],
            ),
            (
                "context",
                IntelligenceRequest(
                    operation="context",
                    targets=(SymbolSelector("Caller"),),
                    bounds=IntelligenceBounds(max_depth=1, max_items=900),
                ),
                ["context", "Caller"],
            ),
            (
                "impact",
                IntelligenceRequest(
                    operation="impact",
                    targets=(SymbolSelector("Target"),),
                    direction="incoming",
                    bounds=IntelligenceBounds(max_depth=3, max_items=2000),
                ),
                ["impact", "Target"],
            ),
            (
                "diagnostics",
                IntelligenceRequest(
                    operation="diagnostics",
                    bounds=IntelligenceBounds(max_depth=1, max_items=250),
                ),
                ["diagnostics"],
            ),
        )
        with TemporaryDirectory() as directory:
            graph_path = Path(directory) / "graph.json"
            graph.save(graph_path)
            state = DashboardState()
            state.load_graph(graph, Path.cwd())
            server = create_server(state, port=0)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for operation, request, cli_tail in vectors:
                    with self.subTest(operation=operation):
                        direct = IntelligenceKernel(graph).execute(request).to_dict()
                        stdout = io.StringIO()
                        with contextlib.redirect_stdout(stdout):
                            code = run(
                                [
                                    "intelligence",
                                    *cli_tail,
                                    str(graph_path),
                                    "--contract-version",
                                    "1",
                                    "--json",
                                ]
                                if operation == "diagnostics"
                                else [
                                    "intelligence",
                                    cli_tail[0],
                                    str(graph_path),
                                    cli_tail[1],
                                    "--contract-version",
                                    "1",
                                    "--json",
                                ]
                            )
                        self.assertEqual(0, code)
                        self.assertEqual(direct, json.loads(stdout.getvalue()))

                        connection = HTTPConnection(
                            "127.0.0.1", server.server_port, timeout=3
                        )
                        body = json.dumps(request.to_dict()).encode("utf-8")
                        connection.request(
                            "POST",
                            f"/api/v1/intelligence/{operation}",
                            body=body,
                            headers={
                                "Content-Type": "application/json",
                                "Content-Length": str(len(body)),
                            },
                        )
                        response = connection.getresponse()
                        http = json.loads(response.read())
                        connection.close()
                        self.assertEqual(200, response.status)
                        http["graph_identity"]["snapshot_revision"] = None
                        self.assertEqual(direct, http)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_evidence_state_vectors_and_graph_immutability(self) -> None:
        center = make_node("Center")
        nodes = [make_node(name) for name in ("Stale", "Unavailable", "Unknown")]
        edges = [
            make_edge(
                center,
                nodes[0],
                edge_id="edge:stale",
                location=SourceLocation("EA.mq5", 1, 1),
            ),
            make_edge(center, nodes[1], edge_id="edge:unavailable"),
            make_edge(
                center,
                nodes[2],
                edge_id="edge:unknown",
                location=SourceLocation("EA.mq5", 2, 1),
            ),
        ]
        states = {
            "edge:stale": ("stale", "source_changed"),
            "edge:unavailable": ("unavailable", "source_missing"),
            "edge:unknown": ("unknown", "freshness_not_proven"),
        }
        graph = build_graph([center, *nodes], edges)
        before = graph.to_json()
        result = IntelligenceKernel(
            graph, evidence_probe=lambda edge: states[edge.id]
        ).execute(
            IntelligenceRequest(
                operation="context",
                targets=(SymbolSelector("Center"),),
                bounds=IntelligenceBounds(max_depth=1, max_items=20),
            )
        )
        evidence = {item.id: item.evidence for item in result.relationships}
        self.assertEqual("stale", evidence["edge:stale"].state)
        self.assertEqual("unavailable", evidence["edge:unavailable"].state)
        self.assertIsNone(evidence["edge:unavailable"].location)
        self.assertEqual("unknown", evidence["edge:unknown"].state)
        self.assertEqual(before, graph.to_json())

    def test_cli_and_http_preserve_stable_validation_errors(self) -> None:
        graph = build_graph([make_node("OnTick")])
        with TemporaryDirectory() as directory:
            graph_path = Path(directory) / "graph.json"
            graph.save(graph_path)
            for arguments, expected in (
                (
                    [
                        "intelligence",
                        "query",
                        str(graph_path),
                        "OnTick",
                        "--contract-version",
                        "2.0.0",
                        "--json",
                    ],
                    "unsupported_contract_version",
                ),
                (
                    [
                        "intelligence",
                        "query",
                        str(graph_path),
                        "OnTick",
                        "--max-depth",
                        "6",
                        "--json",
                    ],
                    "invalid_parameter",
                ),
            ):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    code = run(arguments)
                self.assertEqual(1, code)
                self.assertEqual(
                    expected, json.loads(stderr.getvalue())["error"]["code"]
                )

        state = DashboardState()
        state.load_graph(graph, Path.cwd())
        server = create_server(state, port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = HTTPConnection(
                "127.0.0.1", server.server_port, timeout=3
            )
            payload = {
                "contract_version": "2.0.0",
                "targets": [{"value": "OnTick", "kind": None}],
            }
            body = json.dumps(payload).encode("utf-8")
            connection.request(
                "POST",
                "/api/v1/intelligence/query",
                body=body,
                headers={"Content-Length": str(len(body))},
            )
            response = connection.getresponse()
            error = json.loads(response.read())
            connection.close()
            self.assertEqual(409, response.status)
            self.assertEqual(
                "unsupported_contract_version", error["error"]["code"]
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
