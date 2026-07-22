from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mql5_codegraph.indexer import analyze_repository


FIXTURE = Path(__file__).parent / "fixtures" / "basic_ea"


class IndexerTests(TestCase):
    def test_builds_resolved_and_runtime_graph(self) -> None:
        graph = analyze_repository(FIXTURE)
        names = {node.qualified_name for node in graph.nodes.values()}
        relationships = {(graph.nodes[edge.source].name, edge.relationship,
                          graph.nodes[edge.target].name) for edge in graph.edges.values()}
        self.assertIn("CRiskManager::CalculateLots", names)
        self.assertIn(("BasicEA.mq5", "includes", "Risk.mqh"), relationships)
        self.assertIn(("MetaTrader 5 Terminal", "runtime_dispatches", "OnTick"), relationships)
        self.assertIn(("OrderSend", "may_trigger_event", "OnTradeTransaction"), relationships)
        self.assertTrue(any(item.code == "PARSE001" for item in graph.diagnostics))

    def test_serialization_is_deterministic(self) -> None:
        first = analyze_repository(FIXTURE).to_json()
        second = analyze_repository(FIXTURE).to_json()
        self.assertEqual(first, second)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "graph.json"
            analyze_repository(FIXTURE).save(path)
            self.assertEqual(first, path.read_text(encoding="utf-8"))
