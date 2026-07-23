from dataclasses import FrozenInstanceError
from unittest import TestCase

from mql5_codegraph.graph import SourceLocation
from mql5_codegraph.intelligence.index import GraphIndex
from mql5_codegraph.intelligence.matching import resolve_target
from mql5_codegraph.intelligence.models import SymbolSelector

from .helpers import build_graph, make_edge, make_node


class GraphIndexTests(TestCase):
    def setUp(self) -> None:
        self.alpha = make_node(
            "Calculate",
            qualified_name="Alpha::Calculate",
            kind="method",
            location=SourceLocation("Alpha.mqh", 2, 3),
        )
        self.beta = make_node(
            "Calculate",
            qualified_name="Beta::Calculate",
            kind="method",
            location=SourceLocation("Beta.mqh", 4, 5),
        )
        self.caller = make_node("OnTick", kind="event_handler")
        self.edges = (
            make_edge(self.caller, self.beta, origin="resolved"),
            make_edge(self.caller, self.alpha, origin="resolved"),
        )

    def test_index_is_deterministic_and_does_not_mutate_source(self) -> None:
        first_graph = build_graph(
            [self.beta, self.caller, self.alpha], reversed(self.edges)
        )
        second_graph = build_graph(
            [self.alpha, self.caller, self.beta], self.edges
        )
        before = first_graph.to_json()
        first = GraphIndex(first_graph)
        second = GraphIndex(second_graph)
        self.assertEqual(first.node_ids, second.node_ids)
        self.assertEqual(first.edge_ids, second.edge_ids)
        self.assertEqual(
            tuple(edge.id for edge in first.outgoing[self.caller.id]),
            tuple(edge.id for edge in second.outgoing[self.caller.id]),
        )
        self.assertEqual(before, first_graph.to_json())

    def test_index_collections_are_read_only(self) -> None:
        index = GraphIndex(build_graph([self.alpha, self.caller], self.edges[:1]))
        with self.assertRaises(TypeError):
            index.nodes[self.alpha.id] = self.caller
        with self.assertRaises((AttributeError, TypeError, FrozenInstanceError)):
            index.node_ids += ("other",)


class MatchingTests(GraphIndexTests):
    def setUp(self) -> None:
        super().setUp()
        self.index = GraphIndex(
            build_graph([self.beta, self.caller, self.alpha], self.edges)
        )

    def test_match_ranking_exact_id_qualified_short_and_substring(self) -> None:
        vectors = (
            (self.alpha.id, 0, (self.alpha.id,)),
            ("Alpha::Calculate", 1, (self.alpha.id,)),
            ("Calculate", 2, (self.alpha.id, self.beta.id)),
            ("lcul", 3, (self.alpha.id, self.beta.id)),
        )
        for value, rank, ids in vectors:
            with self.subTest(value=value):
                result = resolve_target(self.index, SymbolSelector(value))
                self.assertEqual(ids, tuple(item.node_id for item in result.candidates))
                self.assertTrue(all(item.match_rank == rank for item in result.candidates))
        self.assertEqual(
            "ambiguous",
            resolve_target(self.index, SymbolSelector("Calculate")).status,
        )

    def test_kind_filter_and_not_found_remain_explicit(self) -> None:
        mismatch = resolve_target(
            self.index, SymbolSelector("Calculate", kind="function")
        )
        self.assertEqual("no_match", mismatch.status)
        self.assertEqual((), mismatch.candidates)
        missing = resolve_target(self.index, SymbolSelector("DoesNotExist"))
        self.assertEqual("no_match", missing.status)
