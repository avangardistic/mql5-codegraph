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

    def test_resolves_object_method_by_receiver_type_instead_of_same_scope(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Engine.mqh").write_text(
                """
class CWorker
  {
public:
   void Run()
     {
     }
  };

class CEngine
  {
private:
   CWorker m_worker;

public:
   void OnTick()
     {
      m_worker.Run();
     }
  };
""",
                encoding="utf-8",
            )
            (root / "ReceiverEA.mq5").write_text(
                """
#include "Engine.mqh"

CEngine g_engine;

void Run()
  {
  }

void OnTick()
  {
   g_engine.OnTick();
  }
""",
                encoding="utf-8",
            )

            graph = analyze_repository(root)

        global_handler = next(
            node for node in graph.nodes.values()
            if node.qualified_name == "OnTick"
        )
        engine_method = next(
            node for node in graph.nodes.values()
            if node.qualified_name == "CEngine::OnTick"
        )
        worker_method = next(
            node for node in graph.nodes.values()
            if node.qualified_name == "CWorker::Run"
        )
        global_call_edges = [
            edge for edge in graph.edges.values()
            if edge.source == global_handler.id and edge.relationship == "calls"
        ]
        member_call_edges = [
            edge for edge in graph.edges.values()
            if edge.source == engine_method.id and edge.relationship == "calls"
        ]

        self.assertEqual([engine_method.id], [edge.target for edge in global_call_edges])
        self.assertEqual(1.0, global_call_edges[0].confidence)
        self.assertEqual("g_engine", global_call_edges[0].attributes["qualifier"])
        self.assertEqual([worker_method.id], [edge.target for edge in member_call_edges])
        self.assertEqual(1.0, member_call_edges[0].confidence)
        self.assertEqual("m_worker", member_call_edges[0].attributes["qualifier"])
