import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from xml.etree import ElementTree as ET

from mql5_codegraph.cli import run


FIXTURE = Path(__file__).parent / "fixtures" / "basic_ea"


class CliTests(TestCase):
    def test_analyze_query_impact_and_export(self) -> None:
        with TemporaryDirectory() as directory:
            graph_path = Path(directory) / "graph.json"
            graphml_path = Path(directory) / "graph.graphml"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, run(["analyze", str(FIXTURE), "--output", str(graph_path), "--json"]))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(0, run(["query", str(graph_path), "OnTick", "--json"]))
            matches = json.loads(output.getvalue())
            self.assertEqual("OnTick", matches[0]["name"])

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(0, run(["impact", str(graph_path), "CalculateLots", "--json"]))
            impacted = json.loads(output.getvalue())
            self.assertTrue(any(item["node"]["name"] == "OnTick" for item in impacted))

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, run(["export", str(graph_path), "--format", "graphml",
                                         "--output", str(graphml_path), "--json"]))
            root = ET.parse(graphml_path).getroot()
            self.assertTrue(root.tag.endswith("graphml"))
            canonical_ids = {item["id"] for item in json.loads(graph_path.read_text(encoding="utf-8"))["nodes"]}
            graphml_ids = {element.attrib["id"] for element in root.iter() if element.tag.endswith("node")}
            self.assertEqual(canonical_ids, graphml_ids)
