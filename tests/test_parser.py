from pathlib import Path
from unittest import TestCase

from mql5_codegraph.parser import parse_source


FIXTURE = Path(__file__).parent / "fixtures" / "basic_ea"


class ParserTests(TestCase):
    def test_extracts_handlers_functions_and_calls(self) -> None:
        source = (FIXTURE / "BasicEA.mq5").read_text(encoding="utf-8")
        parsed = parse_source(source, "BasicEA.mq5")
        declarations = {(item.kind, item.qualified_name) for item in parsed.declarations}
        calls = {(item.caller, item.name) for item in parsed.calls}
        self.assertIn(("event_handler", "OnTick"), declarations)
        self.assertIn(("function", "SubmitOrder"), declarations)
        self.assertIn(("OnTick", "CalculateLots"), calls)
        self.assertIn(("SubmitOrder", "OrderSend"), calls)
        self.assertNotIn(("OnTimer", "GhostCall"), calls)

    def test_extracts_class_method(self) -> None:
        source = (FIXTURE / "Risk.mqh").read_text(encoding="utf-8")
        parsed = parse_source(source, "Risk.mqh")
        declarations = {(item.kind, item.qualified_name) for item in parsed.declarations}
        self.assertIn(("class", "CRiskManager"), declarations)
        self.assertIn(("method", "CRiskManager::CalculateLots"), declarations)

    def test_preserves_receiver_types_for_object_method_calls(self) -> None:
        parsed = parse_source(
            """
class CEngine
  {
private:
   CWorker m_worker;
public:
   void Run()
     {
      CLocalState local_state;
      m_worker.Evaluate();
      local_state.Reset();
     }

   void Refresh(CInput &input)
     {
      input.Update();
     }
  };

CEngine g_engine;

void OnTick()
  {
   g_engine.Run();
  }
""",
            "ReceiverEA.mq5",
        )

        calls = {
            (item.caller, item.qualifier, item.name): item.receiver_type
            for item in parsed.calls
        }
        self.assertEqual("CWorker", calls[("CEngine::Run", "m_worker", "Evaluate")])
        self.assertEqual("CLocalState", calls[("CEngine::Run", "local_state", "Reset")])
        self.assertEqual("CInput", calls[("CEngine::Refresh", "input", "Update")])
        self.assertEqual("CEngine", calls[("OnTick", "g_engine", "Run")])

    def test_recovers_from_unmatched_brace(self) -> None:
        source = (FIXTURE / "Malformed.mqh").read_text(encoding="utf-8")
        parsed = parse_source(source, "Malformed.mqh")
        self.assertTrue(parsed.diagnostics)
        self.assertIn("Recoverable", {item.name for item in parsed.declarations})
