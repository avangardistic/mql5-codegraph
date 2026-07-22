from http.client import HTTPConnection
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic, sleep
from unittest import TestCase

from mql5_codegraph.web.api import ApiError, DashboardApi
from mql5_codegraph.web.server import create_server
from mql5_codegraph.web.state import DashboardState


FIXTURE = Path(__file__).parent / "fixtures" / "basic_ea"


def ready_state() -> DashboardState:
    state = DashboardState()
    job = state.start_analysis(FIXTURE)
    deadline = monotonic() + 3
    while monotonic() < deadline:
        current = state.get_job(job.id)
        if current and current.status == "completed":
            return state
        sleep(0.01)
    raise AssertionError("fixture analysis timed out")


class DashboardApiTests(TestCase):
    def setUp(self) -> None:
        self.state = ready_state()
        self.api = DashboardApi(self.state)

    def test_health_status_and_bounded_projection(self) -> None:
        self.assertTrue(self.api.health()["ready"])
        projection = self.api.graph({"limit": ["5"]})
        self.assertLessEqual(projection["visible_nodes"], 5)
        self.assertEqual(16, projection["total_nodes"])
        self.assertIn("event_handler", projection["available_kinds"])

    def test_query_context_and_impact_contracts(self) -> None:
        query = self.api.query({"q": ["CalculateLots"]})
        self.assertEqual("CRiskManager::CalculateLots", query["results"][0]["qualified_name"])
        node_id = query["results"][0]["id"]
        context = self.api.context({"symbol": [node_id], "depth": ["1"]})
        self.assertTrue(context["nodes"])
        impact = self.api.impact({"symbol": [node_id], "depth": ["3"]})
        self.assertTrue(any(item["node"]["name"] == "OnTick" for item in impact["results"]))

    def test_diagnostics_and_safe_source_evidence(self) -> None:
        diagnostics = self.api.diagnostics({"severity": ["warning"]})
        self.assertGreaterEqual(diagnostics["matched"], 1)
        source = self.api.source({"file": ["BasicEA.mq5"], "line": ["12"]})
        self.assertIn("void OnTick", source["content"])
        self.assertEqual(12, source["highlight_line"])
        with self.assertRaises(ApiError) as outside:
            self.api.source({"file": ["../outside.mq5"]})
        self.assertEqual(403, outside.exception.status)
        with self.assertRaises(ApiError) as denied:
            self.api.source({"file": ["BasicEA.txt"]})
        self.assertIn(denied.exception.status, {403, 404})

    def test_invalid_parameters_are_structured_errors(self) -> None:
        with self.assertRaises(ApiError) as missing:
            self.api.query({})
        self.assertEqual("missing_query", missing.exception.code)
        with self.assertRaises(ApiError) as depth:
            self.api.context({"symbol": ["OnTick"], "depth": ["99"]})
        self.assertEqual("invalid_parameter", depth.exception.code)


class DashboardHttpTests(TestCase):
    def test_http_health_static_and_malformed_json(self) -> None:
        state = ready_state()
        with TemporaryDirectory() as directory:
            static_root = Path(directory)
            (static_root / "index.html").write_text("<!doctype html><title>dashboard</title>", encoding="utf-8")
            server = create_server(state, port=0, static_root=static_root)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
                connection.request("GET", "/api/health")
                response = connection.getresponse()
                payload = json.loads(response.read())
                self.assertEqual(200, response.status)
                self.assertTrue(payload["ok"])
                self.assertEqual("nosniff", response.getheader("X-Content-Type-Options"))

                connection.request("GET", "/does-not-exist")
                response = connection.getresponse()
                self.assertEqual(200, response.status)
                self.assertIn(b"dashboard", response.read())

                connection.request("POST", "/api/analyze", body=b"{bad",
                                   headers={"Content-Type": "application/json", "Content-Length": "4"})
                response = connection.getresponse()
                payload = json.loads(response.read())
                self.assertEqual(400, response.status)
                self.assertEqual("invalid_json", payload["error"]["code"])
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
