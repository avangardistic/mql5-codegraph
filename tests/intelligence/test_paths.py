import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from mql5_codegraph.graph import SourceLocation
from mql5_codegraph.indexer import analyze_repository
from mql5_codegraph.intelligence import paths as path_module
from mql5_codegraph.intelligence.errors import IntelligenceError
from mql5_codegraph.intelligence.index import GraphIndex
from mql5_codegraph.intelligence.kernel import IntelligenceKernel
from mql5_codegraph.intelligence.models import (
    IntelligenceBounds,
    IntelligenceRequest,
    SymbolSelector,
)
from mql5_codegraph.intelligence.paths import find_directed_paths

from .helpers import build_graph, make_edge, make_node


FIXTURE = Path(__file__).parents[1] / "fixtures" / "basic_ea"


class DirectedPathTests(TestCase):
    def test_us2_acceptance_slice_on_reference_fixture(self) -> None:
        graph = analyze_repository(FIXTURE)
        before = graph.to_json()
        result = IntelligenceKernel(
            graph,
            evidence_probe=lambda item: ("available", None),
        ).execute(
            IntelligenceRequest(
                operation="path",
                targets=(
                    SymbolSelector("OnTick"),
                    SymbolSelector("CalculateLots"),
                ),
                direction="outgoing",
                bounds=IntelligenceBounds(
                    max_depth=5,
                    max_paths=3,
                    max_expansions=10_000,
                ),
            )
        )

        self.assertEqual(("matched", "matched"), tuple(r.status for r in result.resolution))
        self.assertEqual("complete", result.completion.reason)
        self.assertTrue(result.completion.search_complete)
        self.assertFalse(result.completion.truncated)
        self.assertEqual(1, len(result.paths))

        path = result.paths[0]
        self.assertEqual(1, path.rank)
        self.assertEqual("evidence_first_v1", path.ranking_policy)
        self.assertEqual(
            ("OnTick", "CalculateLots"),
            tuple(graph.nodes[node_id].name for node_id in path.node_ids),
        )
        self.assertEqual(len(path.node_ids) - 1, len(path.hops))
        for hop in path.hops:
            self.assertEqual("forward", hop.direction)
            self.assertTrue(hop.relationship)
            self.assertIn(
                hop.evidence.origin,
                {"extracted", "resolved", "runtime", "inferred"},
            )
            self.assertGreaterEqual(hop.evidence.confidence, 0.0)
            self.assertLessEqual(hop.evidence.confidence, 1.0)
            self.assertIsNotNone(hop.evidence.location)
            self.assertEqual("available", hop.evidence.state)

        self.assertEqual(before, graph.to_json())

    def test_kernel_dispatch_serializes_the_normalized_path_envelope(self) -> None:
        source = make_node("OnTick", node_id="node:on-tick")
        target = make_node("CalculateLots", node_id="node:calculate-lots")
        edge = make_edge(
            source,
            target,
            edge_id="edge:on-tick-calculate-lots",
            origin="resolved",
            confidence=0.9,
            location=SourceLocation("Expert.mq5", 12, 5),
        )
        graph = build_graph([target, source], [edge])
        before = graph.to_json()
        request = IntelligenceRequest(
            operation="path",
            targets=(
                SymbolSelector(source.id),
                SymbolSelector(target.id),
            ),
            direction="outgoing",
            bounds=IntelligenceBounds(
                max_depth=5,
                max_paths=3,
                max_expansions=100,
            ),
        )

        result = IntelligenceKernel(
            graph,
            snapshot_revision=4,
            evidence_probe=lambda item: ("available", None),
        ).execute(request)
        payload = result.to_dict()

        self.assertEqual("path", result.operation)
        self.assertEqual(("matched", "matched"), tuple(r.status for r in result.resolution))
        self.assertEqual(1, len(result.paths))
        self.assertEqual(
            (source.id, target.id),
            result.paths[0].node_ids,
        )
        self.assertEqual("available", result.paths[0].hops[0].evidence.state)
        self.assertEqual(request.bounds.to_dict(), payload["limits_applied"])
        self.assertEqual(payload, json.loads(result.to_json()))
        self.assertEqual([], payload["relationships"])
        self.assertEqual([], payload["diagnostics"])
        self.assertIsNone(payload["context_package"])
        self.assertEqual(before, graph.to_json())

    def test_kernel_reuses_target_distances_within_one_snapshot(self) -> None:
        source = make_node("Source", node_id="node:source")
        target = make_node("Target", node_id="node:target")
        graph = build_graph(
            [source, target],
            [make_edge(source, target, edge_id="edge:source-target")],
        )
        request = IntelligenceRequest(
            operation="path",
            targets=(SymbolSelector(source.id), SymbolSelector(target.id)),
            direction="outgoing",
            bounds=IntelligenceBounds(max_depth=1),
        )
        first_kernel = IntelligenceKernel(graph, snapshot_revision=1)
        second_kernel = IntelligenceKernel(graph, snapshot_revision=2)

        with patch.object(
            path_module,
            "_minimum_hops_to_targets",
            wraps=path_module._minimum_hops_to_targets,
        ) as distance_builder:
            first = first_kernel.execute(request)
            repeated = first_kernel.execute(request)
            replaced = second_kernel.execute(request)

        self.assertEqual(first.to_dict(), repeated.to_dict())
        self.assertEqual(first.paths, replaced.paths)
        self.assertEqual(2, distance_builder.call_count)
        self.assertEqual(1, first.graph_identity.snapshot_revision)
        self.assertEqual(2, replaced.graph_identity.snapshot_revision)

    def test_kernel_target_distance_cache_is_bounded_lru(self) -> None:
        source = make_node("Source", node_id="node:source")
        targets = tuple(
            make_node(f"Target{position}", node_id=f"node:target-{position}")
            for position in range(65)
        )
        graph = build_graph(
            [source, *targets],
            (
                make_edge(
                    source,
                    target,
                    edge_id=f"edge:source-target-{position}",
                )
                for position, target in enumerate(targets)
            ),
        )
        kernel = IntelligenceKernel(graph)

        def request_for(target):
            return IntelligenceRequest(
                operation="path",
                targets=(SymbolSelector(source.id), SymbolSelector(target.id)),
                direction="outgoing",
                bounds=IntelligenceBounds(max_depth=1),
            )

        with patch.object(
            path_module,
            "_minimum_hops_to_targets",
            wraps=path_module._minimum_hops_to_targets,
        ) as distance_builder:
            for target in targets:
                kernel.execute(request_for(target))
            self.assertEqual(65, distance_builder.call_count)

            kernel.execute(request_for(targets[-1]))
            self.assertEqual(65, distance_builder.call_count)

            kernel.execute(request_for(targets[0]))
            self.assertEqual(66, distance_builder.call_count)

    def test_kernel_target_distance_cache_keys_direction_and_relationships(self) -> None:
        source = make_node("Source", node_id="node:source")
        middle = make_node("Middle", node_id="node:middle")
        target = make_node("Target", node_id="node:target")
        graph = build_graph(
            [source, middle, target],
            (
                make_edge(source, middle, edge_id="edge:source-middle"),
                make_edge(middle, target, edge_id="edge:middle-target"),
            ),
        )
        kernel = IntelligenceKernel(graph)

        def request_for(direction, relationship_types=()):
            return IntelligenceRequest(
                operation="path",
                targets=(SymbolSelector(source.id), SymbolSelector(target.id)),
                direction=direction,
                relationship_types=relationship_types,
                bounds=IntelligenceBounds(max_depth=2),
            )

        with patch.object(
            path_module,
            "_minimum_hops_to_targets",
            wraps=path_module._minimum_hops_to_targets,
        ) as distance_builder:
            filtered = kernel.execute(request_for("outgoing", ("references",)))
            connected = kernel.execute(request_for("outgoing", ("calls",)))
            reverse = kernel.execute(request_for("incoming", ("calls",)))
            repeated = kernel.execute(request_for("outgoing", ("calls",)))

        self.assertEqual("not_connected", filtered.completion.reason)
        self.assertEqual((source.id, middle.id, target.id), connected.paths[0].node_ids)
        self.assertEqual("not_connected", reverse.completion.reason)
        self.assertEqual(connected.to_dict(), repeated.to_dict())
        self.assertEqual(3, distance_builder.call_count)

    def test_kernel_searches_all_ambiguous_candidates_and_preserves_no_match(self) -> None:
        alpha = make_node(
            "Source",
            qualified_name="Alpha.Source",
            node_id="node:alpha-source",
        )
        beta = make_node(
            "Source",
            qualified_name="Beta.Source",
            node_id="node:beta-source",
        )
        target = make_node("Target", node_id="node:target")
        edge = make_edge(alpha, target, edge_id="edge:alpha-target")
        kernel = IntelligenceKernel(build_graph([target, beta, alpha], [edge]))
        bounds = IntelligenceBounds(max_depth=2, max_paths=3, max_expansions=20)

        ambiguous = kernel.execute(
            IntelligenceRequest(
                operation="path",
                targets=(SymbolSelector("Source"), SymbolSelector("Target")),
                direction="outgoing",
                bounds=bounds,
            )
        )
        self.assertEqual(
            ("ambiguous", "matched"),
            tuple(resolution.status for resolution in ambiguous.resolution),
        )
        self.assertEqual(
            (alpha.id, target.id),
            ambiguous.paths[0].node_ids,
        )

        missing = kernel.execute(
            IntelligenceRequest(
                operation="path",
                targets=(SymbolSelector("Source"), SymbolSelector("Missing")),
                direction="outgoing",
                bounds=bounds,
            )
        )
        self.assertEqual(
            ("ambiguous", "no_match"),
            tuple(resolution.status for resolution in missing.resolution),
        )
        self.assertEqual((), missing.paths)
        self.assertEqual("no_match", missing.completion.reason)

    def test_kernel_path_requires_exactly_two_selectors(self) -> None:
        kernel = IntelligenceKernel(build_graph([make_node("Source")]))

        for targets in ((), (SymbolSelector("Source"),)):
            with self.subTest(target_count=len(targets)):
                with self.assertRaises(IntelligenceError) as raised:
                    kernel.execute(
                        IntelligenceRequest(
                            operation="path",
                            targets=targets,
                            direction="outgoing",
                        )
                    )
                self.assertEqual("missing_target", raised.exception.code)
                self.assertEqual("targets", raised.exception.field)

    def test_every_hop_preserves_direction_origin_confidence_and_location(self) -> None:
        on_tick = make_node("OnTick", node_id="node:on-tick")
        dispatch = make_node("Dispatch", node_id="node:dispatch")
        strategy = make_node("Strategy", node_id="node:strategy")
        risk = make_node("Risk", node_id="node:risk")
        calculate_lots = make_node("CalculateLots", node_id="node:calculate-lots")
        locations = (
            SourceLocation("Expert.mq5", 10, 3),
            SourceLocation("Expert.mq5", 20, 5),
            SourceLocation("Runtime.mqh", 30, 7),
            SourceLocation("Risk.mqh", 40, 9),
        )
        edges = (
            make_edge(
                on_tick,
                dispatch,
                edge_id="edge:01-extracted",
                origin="extracted",
                confidence=1.0,
                location=locations[0],
            ),
            make_edge(
                dispatch,
                strategy,
                edge_id="edge:02-resolved",
                origin="resolved",
                confidence=0.95,
                location=locations[1],
            ),
            make_edge(
                strategy,
                risk,
                edge_id="edge:03-runtime",
                relationship="runtime_dispatches",
                origin="runtime",
                confidence=0.9,
                location=locations[2],
            ),
            make_edge(
                risk,
                calculate_lots,
                edge_id="edge:04-inferred",
                relationship="may_call",
                origin="inferred",
                confidence=0.6,
                location=locations[3],
            ),
        )
        states = {
            edges[0].id: ("available", None),
            edges[1].id: ("stale", "source_changed"),
            edges[2].id: ("unavailable", "source_missing"),
            edges[3].id: ("unknown", "probe_indeterminate"),
        }
        result = find_directed_paths(
            GraphIndex(
                build_graph(
                    [calculate_lots, risk, strategy, dispatch, on_tick],
                    reversed(edges),
                )
            ),
            on_tick.id,
            calculate_lots.id,
            IntelligenceBounds(max_depth=5, max_paths=3, max_expansions=100),
            evidence_probe=lambda edge: states[edge.id],
        )

        self.assertEqual(1, len(result.paths))
        path = result.paths[0]
        self.assertEqual(
            (
                on_tick.id,
                dispatch.id,
                strategy.id,
                risk.id,
                calculate_lots.id,
            ),
            path.node_ids,
        )
        self.assertEqual(("forward",) * 4, tuple(hop.direction for hop in path.hops))
        self.assertEqual(
            ("extracted", "resolved", "runtime", "inferred"),
            tuple(hop.evidence.origin for hop in path.hops),
        )
        self.assertEqual(
            (1.0, 0.95, 0.9, 0.6),
            tuple(hop.evidence.confidence for hop in path.hops),
        )
        self.assertEqual(locations, tuple(hop.evidence.location for hop in path.hops))
        self.assertEqual(
            ("available", "stale", "unavailable", "unknown"),
            tuple(hop.evidence.state for hop in path.hops),
        )
        self.assertEqual(
            (None, "source_changed", "source_missing", "probe_indeterminate"),
            tuple(hop.evidence.state_reason for hop in path.hops),
        )
        self.assertTrue(result.completion.search_complete)
        self.assertFalse(result.completion.truncated)
        self.assertEqual("complete", result.completion.reason)

    def test_locationless_evidence_is_unknown_without_a_probe(self) -> None:
        source = make_node("Source", node_id="node:source")
        target = make_node("Target", node_id="node:target")
        edge = make_edge(
            source,
            target,
            edge_id="edge:locationless",
            origin="resolved",
            confidence=0.75,
            location=None,
        )

        result = find_directed_paths(
            GraphIndex(build_graph([source, target], [edge])),
            source.id,
            target.id,
            IntelligenceBounds(max_depth=1),
        )

        evidence = result.paths[0].hops[0].evidence
        self.assertIsNone(evidence.location)
        self.assertEqual("unknown", evidence.state)
        self.assertEqual("location_missing", evidence.state_reason)

    def test_reverse_direction_uses_incoming_edges_and_marks_reverse_hops(self) -> None:
        source = make_node("Source", node_id="node:source")
        middle = make_node("Middle", node_id="node:middle")
        target = make_node("Target", node_id="node:target")
        first = make_edge(source, middle, edge_id="edge:01")
        second = make_edge(middle, target, edge_id="edge:02")
        index = GraphIndex(build_graph([source, middle, target], [first, second]))

        result = find_directed_paths(
            index,
            target.id,
            source.id,
            IntelligenceBounds(max_depth=2),
            direction="incoming",
        )

        self.assertEqual((target.id, middle.id, source.id), result.paths[0].node_ids)
        self.assertEqual(
            ("edge:02", "edge:01"),
            tuple(hop.edge_id for hop in result.paths[0].hops),
        )
        self.assertEqual(
            ("reverse", "reverse"),
            tuple(hop.direction for hop in result.paths[0].hops),
        )

    def test_cycles_produce_only_simple_paths(self) -> None:
        source = make_node("Source", node_id="node:source")
        middle = make_node("Middle", node_id="node:middle")
        target = make_node("Target", node_id="node:target")
        edges = (
            make_edge(source, middle, edge_id="edge:source-middle"),
            make_edge(middle, source, edge_id="edge:middle-source"),
            make_edge(middle, target, edge_id="edge:middle-target"),
        )

        result = find_directed_paths(
            GraphIndex(build_graph([source, middle, target], edges)),
            source.id,
            target.id,
            IntelligenceBounds(max_depth=5, max_paths=5, max_expansions=100),
        )

        self.assertEqual(1, len(result.paths))
        self.assertEqual(
            (source.id, middle.id, target.id),
            result.paths[0].node_ids,
        )
        self.assertEqual(
            len(result.paths[0].node_ids),
            len(set(result.paths[0].node_ids)),
        )
        self.assertLessEqual(result.completion.explored_edges, 3)

    def test_evidence_first_ranking_beats_shortest_path(self) -> None:
        source = make_node("Source", node_id="node:source")
        strong_middle = make_node("Strong", node_id="node:strong")
        weak_middle = make_node("Weak", node_id="node:weak")
        target = make_node("Target", node_id="node:target")
        edges = (
            make_edge(
                source,
                target,
                edge_id="edge:00-short-inferred",
                origin="inferred",
                confidence=0.99,
            ),
            make_edge(
                source,
                strong_middle,
                edge_id="edge:20-strong-a",
                origin="extracted",
                confidence=0.9,
            ),
            make_edge(
                strong_middle,
                target,
                edge_id="edge:20-strong-b",
                origin="resolved",
                confidence=0.9,
            ),
            make_edge(
                source,
                weak_middle,
                edge_id="edge:10-weak-a",
                origin="extracted",
                confidence=0.8,
            ),
            make_edge(
                weak_middle,
                target,
                edge_id="edge:10-weak-b",
                origin="resolved",
                confidence=0.8,
            ),
        )
        result = find_directed_paths(
            GraphIndex(build_graph([target, weak_middle, strong_middle, source], edges)),
            source.id,
            target.id,
            IntelligenceBounds(max_depth=2, max_paths=3, max_expansions=100),
        )

        self.assertEqual(
            (
                (source.id, strong_middle.id, target.id),
                (source.id, weak_middle.id, target.id),
                (source.id, target.id),
            ),
            tuple(path.node_ids for path in result.paths),
        )
        self.assertEqual((1, 2, 3), tuple(path.rank for path in result.paths))
        self.assertTrue(
            all(path.ranking_policy == "evidence_first_v1" for path in result.paths)
        )

    def test_fresh_evidence_ranks_before_stale_or_unavailable_alternatives(self) -> None:
        source = make_node("Source", node_id="node:source")
        clean = make_node("Clean", node_id="node:clean")
        stale = make_node("Stale", node_id="node:stale")
        unavailable = make_node("Unavailable", node_id="node:unavailable")
        target = make_node("Target", node_id="node:target")
        edges = (
            make_edge(source, stale, edge_id="edge:a-stale-1"),
            make_edge(stale, target, edge_id="edge:a-stale-2"),
            make_edge(source, unavailable, edge_id="edge:b-unavailable-1"),
            make_edge(unavailable, target, edge_id="edge:b-unavailable-2"),
            make_edge(source, clean, edge_id="edge:z-clean-1"),
            make_edge(clean, target, edge_id="edge:z-clean-2"),
        )

        def probe(edge):
            if "stale" in edge.id:
                return ("stale", "source_changed")
            if "unavailable" in edge.id:
                return ("unavailable", "source_missing")
            return ("available", None)

        result = find_directed_paths(
            GraphIndex(
                build_graph(
                    [source, unavailable, stale, clean, target],
                    reversed(edges),
                )
            ),
            source.id,
            target.id,
            IntelligenceBounds(max_depth=2, max_paths=3, max_expansions=100),
            evidence_probe=probe,
        )

        self.assertEqual(
            (source.id, clean.id, target.id),
            result.paths[0].node_ids,
        )
        self.assertEqual(
            (
                ("available", "available"),
                ("stale", "stale"),
                ("unavailable", "unavailable"),
            ),
            tuple(
                tuple(hop.evidence.state for hop in path.hops)
                for path in result.paths
            ),
        )

    def test_equal_alternatives_use_edge_ids_independent_of_insertion_order(self) -> None:
        source = make_node("Source", node_id="node:source")
        alpha = make_node("Alpha", node_id="node:alpha")
        beta = make_node("Beta", node_id="node:beta")
        target = make_node("Target", node_id="node:target")
        edges = (
            make_edge(source, alpha, edge_id="edge:a-1", confidence=0.9),
            make_edge(alpha, target, edge_id="edge:a-2", confidence=0.9),
            make_edge(source, beta, edge_id="edge:b-1", confidence=0.9),
            make_edge(beta, target, edge_id="edge:b-2", confidence=0.9),
        )
        bounds = IntelligenceBounds(max_depth=2, max_paths=2, max_expansions=100)

        first = find_directed_paths(
            GraphIndex(build_graph([source, alpha, beta, target], edges)),
            source.id,
            target.id,
            bounds,
        )
        second = find_directed_paths(
            GraphIndex(
                build_graph(
                    [target, beta, alpha, source],
                    reversed(edges),
                )
            ),
            source.id,
            target.id,
            bounds,
        )

        self.assertEqual(
            (("edge:a-1", "edge:a-2"), ("edge:b-1", "edge:b-2")),
            tuple(tuple(hop.edge_id for hop in path.hops) for path in first.paths),
        )
        self.assertEqual(
            tuple(path.to_dict() for path in first.paths),
            tuple(path.to_dict() for path in second.paths),
        )
        self.assertEqual(first.completion.to_dict(), second.completion.to_dict())

    def test_complete_search_with_capped_output_reports_omitted_paths(self) -> None:
        source = make_node("Source", node_id="node:source")
        alpha = make_node("Alpha", node_id="node:alpha")
        beta = make_node("Beta", node_id="node:beta")
        target = make_node("Target", node_id="node:target")
        edges = (
            make_edge(source, alpha, edge_id="edge:a-1"),
            make_edge(alpha, target, edge_id="edge:a-2"),
            make_edge(source, beta, edge_id="edge:b-1"),
            make_edge(beta, target, edge_id="edge:b-2"),
        )

        result = find_directed_paths(
            GraphIndex(build_graph([source, alpha, beta, target], edges)),
            source.id,
            target.id,
            IntelligenceBounds(max_depth=2, max_paths=1, max_expansions=100),
        )

        self.assertEqual(1, len(result.paths))
        self.assertTrue(result.completion.search_complete)
        self.assertTrue(result.completion.truncated)
        self.assertEqual("max_paths", result.completion.reason)
        self.assertEqual({"paths": 1}, dict(result.completion.omitted_counts))

    def test_path_quota_stops_after_an_omitted_path_is_proven(self) -> None:
        source = make_node("Source", node_id="node:source")
        alternatives = tuple(
            make_node(name, node_id=f"node:{name.casefold()}")
            for name in ("Alpha", "Beta", "Gamma")
        )
        target = make_node("Target", node_id="node:target")
        edges = tuple(
            edge
            for position, alternative in enumerate(alternatives)
            for edge in (
                make_edge(
                    source,
                    alternative,
                    edge_id=f"edge:{position}:first",
                ),
                make_edge(
                    alternative,
                    target,
                    edge_id=f"edge:{position}:second",
                ),
            )
        )

        result = find_directed_paths(
            GraphIndex(build_graph([source, *alternatives, target], edges)),
            source.id,
            target.id,
            IntelligenceBounds(max_depth=2, max_paths=1, max_expansions=100),
        )

        self.assertEqual(1, len(result.paths))
        self.assertFalse(result.completion.search_complete)
        self.assertTrue(result.completion.truncated)
        self.assertEqual("max_paths", result.completion.reason)
        self.assertEqual({"paths": None}, dict(result.completion.omitted_counts))

    def test_target_distance_prunes_dense_disconnected_branches(self) -> None:
        source = make_node("Source", node_id="node:source")
        target = make_node("Target", node_id="node:target")
        dead_ends = tuple(
            make_node(f"Dead{position}", node_id=f"node:dead-{position}")
            for position in range(8)
        )
        edges = [
            make_edge(source, target, edge_id="edge:source-target"),
            *(
                make_edge(
                    source,
                    dead_end,
                    edge_id=f"edge:source-dead-{position}",
                )
                for position, dead_end in enumerate(dead_ends)
            ),
        ]
        edges.extend(
            make_edge(
                left,
                right,
                edge_id=f"edge:dead-{left_position}-{right_position}",
            )
            for left_position, left in enumerate(dead_ends)
            for right_position, right in enumerate(dead_ends)
            if left_position != right_position
        )

        result = find_directed_paths(
            GraphIndex(build_graph([source, target, *dead_ends], edges)),
            source.id,
            target.id,
            IntelligenceBounds(max_depth=5, max_paths=1, max_expansions=20),
        )

        self.assertEqual((source.id, target.id), result.paths[0].node_ids)
        self.assertTrue(result.completion.search_complete)
        self.assertFalse(result.completion.truncated)
        self.assertEqual("complete", result.completion.reason)
        self.assertEqual(9, result.completion.explored_edges)

    def test_disconnected_search_is_not_connected_only_after_exhaustion(self) -> None:
        source = make_node("Source", node_id="node:source")
        reachable = make_node("Reachable", node_id="node:reachable")
        target = make_node("Target", node_id="node:target")
        edge = make_edge(source, reachable, edge_id="edge:reachable")

        result = find_directed_paths(
            GraphIndex(build_graph([source, reachable, target], [edge])),
            source.id,
            target.id,
            IntelligenceBounds(max_depth=5, max_paths=3, max_expansions=100),
        )

        self.assertEqual((), result.paths)
        self.assertTrue(result.completion.search_complete)
        self.assertFalse(result.completion.truncated)
        self.assertEqual("not_connected", result.completion.reason)
        self.assertGreater(result.completion.explored_nodes, 0)
        self.assertGreater(result.completion.explored_edges, 0)

    def test_depth_bound_never_claims_nodes_are_disconnected(self) -> None:
        source = make_node("Source", node_id="node:source")
        middle = make_node("Middle", node_id="node:middle")
        target = make_node("Target", node_id="node:target")
        edges = (
            make_edge(source, middle, edge_id="edge:01"),
            make_edge(middle, target, edge_id="edge:02"),
        )

        result = find_directed_paths(
            GraphIndex(build_graph([source, middle, target], edges)),
            source.id,
            target.id,
            IntelligenceBounds(max_depth=1, max_paths=3, max_expansions=100),
        )

        self.assertEqual((), result.paths)
        self.assertFalse(result.completion.search_complete)
        self.assertTrue(result.completion.truncated)
        self.assertEqual("max_depth", result.completion.reason)
        self.assertEqual({"paths": None}, dict(result.completion.omitted_counts))

    def test_expansion_bound_never_claims_nodes_are_disconnected(self) -> None:
        source = make_node("Source", node_id="node:source")
        first = make_node("First", node_id="node:first")
        second = make_node("Second", node_id="node:second")
        target = make_node("Target", node_id="node:target")
        edges = (
            make_edge(source, first, edge_id="edge:01"),
            make_edge(first, second, edge_id="edge:02"),
            make_edge(second, target, edge_id="edge:03"),
        )

        result = find_directed_paths(
            GraphIndex(build_graph([source, first, second, target], edges)),
            source.id,
            target.id,
            IntelligenceBounds(max_depth=3, max_paths=3, max_expansions=1),
        )

        self.assertEqual((), result.paths)
        self.assertFalse(result.completion.search_complete)
        self.assertTrue(result.completion.truncated)
        self.assertEqual("max_expansions", result.completion.reason)
        self.assertEqual({"paths": None}, dict(result.completion.omitted_counts))
        self.assertLessEqual(result.completion.explored_edges, 1)

    def test_relationship_filter_keeps_unresolved_external_target_visible(self) -> None:
        source = make_node("Source", node_id="node:source")
        external = make_node(
            "ExternalDependency",
            kind="external",
            node_id="node:external-unresolved",
            attributes={"resolution_status": "unresolved"},
        )
        unresolved = make_edge(
            source,
            external,
            edge_id="edge:unresolved",
            relationship="references",
            origin="inferred",
            confidence=0.4,
        )
        ignored = make_edge(
            source,
            external,
            edge_id="edge:ignored",
            relationship="annotates",
            origin="resolved",
        )

        result = find_directed_paths(
            GraphIndex(build_graph([source, external], [ignored, unresolved])),
            source.id,
            external.id,
            IntelligenceBounds(max_depth=1),
            relationship_types=("references",),
        )

        self.assertEqual((source.id, external.id), result.paths[0].node_ids)
        self.assertEqual(("edge:unresolved",), tuple(h.edge_id for h in result.paths[0].hops))
        self.assertEqual("inferred", result.paths[0].hops[0].evidence.origin)
