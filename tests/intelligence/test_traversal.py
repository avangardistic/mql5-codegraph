from unittest import TestCase

from mql5_codegraph.graph import SourceLocation
from mql5_codegraph.intelligence.index import GraphIndex
from mql5_codegraph.intelligence.models import IntelligenceBounds
from mql5_codegraph.intelligence.traversal import (
    traverse_context,
    traverse_impact,
)

from .helpers import build_graph, make_edge, make_node


class TraversalTests(TestCase):
    def setUp(self) -> None:
        self.a = make_node("A")
        self.b = make_node("B")
        self.c = make_node("C")
        self.d = make_node("D")
        self.ab = make_edge(
            self.a,
            self.b,
            relationship="calls",
            origin="extracted",
            location=SourceLocation("Graph.mq5", 1, 1),
        )
        self.bc = make_edge(
            self.b,
            self.c,
            relationship="runtime_dispatches",
            origin="runtime",
            confidence=0.9,
        )
        self.ca = make_edge(
            self.c,
            self.a,
            relationship="calls",
            origin="inferred",
            confidence=0.6,
        )
        self.db = make_edge(
            self.d,
            self.b,
            relationship="annotates",
            origin="resolved",
        )
        self.index = GraphIndex(
            build_graph(
                [self.d, self.c, self.b, self.a],
                [self.db, self.ca, self.bc, self.ab],
            )
        )

    def test_context_respects_direction_and_relationship_filter(self) -> None:
        bounds = IntelligenceBounds(max_depth=1, max_items=20)
        outgoing = traverse_context(
            self.index,
            (self.a.id,),
            bounds,
            direction="outgoing",
            relationship_types=("calls",),
        )
        self.assertEqual((self.a.id, self.b.id), outgoing.node_ids)
        self.assertEqual((self.ab.id,), tuple(item.id for item in outgoing.relationships))

        incoming = traverse_context(
            self.index,
            (self.b.id,),
            bounds,
            direction="incoming",
        )
        self.assertEqual(
            {self.a.id, self.b.id, self.d.id},
            set(incoming.node_ids),
        )

    def test_cycles_are_safe_and_evidence_preserves_origin(self) -> None:
        result = traverse_context(
            self.index,
            (self.a.id,),
            IntelligenceBounds(max_depth=3, max_items=20),
            direction="outgoing",
        )
        self.assertEqual(3, len(result.node_ids))
        evidence = {item.id: item.evidence for item in result.relationships}
        self.assertEqual("extracted", evidence[self.ab.id].origin)
        self.assertEqual("runtime", evidence[self.bc.id].origin)
        self.assertEqual("inferred", evidence[self.ca.id].origin)
        self.assertEqual("unknown", evidence[self.ab.id].state)
        self.assertEqual("probe_not_configured", evidence[self.ab.id].state_reason)

    def test_evidence_probe_reports_stale_without_reinterpreting_edge(self) -> None:
        result = traverse_context(
            self.index,
            (self.a.id,),
            IntelligenceBounds(max_depth=1, max_items=20),
            direction="outgoing",
            evidence_probe=lambda edge: ("stale", "source_changed"),
        )
        evidence = result.relationships[0].evidence
        self.assertEqual("stale", evidence.state)
        self.assertEqual("source_changed", evidence.state_reason)
        self.assertEqual("extracted", evidence.origin)

    def test_depth_and_item_bounds_have_explicit_completion(self) -> None:
        depth_limited = traverse_context(
            self.index,
            (self.a.id,),
            IntelligenceBounds(max_depth=1, max_items=20),
            direction="outgoing",
        )
        self.assertFalse(depth_limited.completion.search_complete)
        self.assertTrue(depth_limited.completion.truncated)
        self.assertEqual("max_depth", depth_limited.completion.reason)

        item_limited = traverse_context(
            self.index,
            (self.a.id,),
            IntelligenceBounds(max_depth=3, max_items=1),
            direction="outgoing",
        )
        self.assertTrue(item_limited.completion.search_complete)
        self.assertTrue(item_limited.completion.truncated)
        self.assertEqual("max_items", item_limited.completion.reason)
        self.assertEqual((self.a.id,), item_limited.node_ids)
        self.assertEqual((), item_limited.relationships)

    def test_impact_uses_incoming_policy_and_empty_seed_is_no_match(self) -> None:
        impact = traverse_impact(
            self.index,
            (self.b.id,),
            IntelligenceBounds(max_depth=2, max_items=20),
        )
        self.assertIn(self.a.id, impact.node_ids)
        self.assertNotIn(self.d.id, impact.node_ids)
        self.assertTrue(
            all(item.relationship != "annotates" for item in impact.relationships)
        )

        missing = traverse_context(
            self.index,
            (),
            IntelligenceBounds(max_depth=1, max_items=20),
        )
        self.assertEqual((), missing.node_ids)
        self.assertEqual("no_match", missing.completion.reason)
