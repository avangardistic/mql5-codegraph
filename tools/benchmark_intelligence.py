"""Deterministic opt-in benchmark for the Intelligence Kernel."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
import os
import platform
from random import Random
from statistics import median
import sys
from time import perf_counter_ns
from typing import Any

from mql5_codegraph.diagnostics import Diagnostic
from mql5_codegraph.graph import (
    CodeGraph,
    GraphEdge,
    GraphNode,
    SourceLocation,
)
from mql5_codegraph.intelligence import (
    IntelligenceBounds,
    IntelligenceKernel,
    IntelligenceRequest,
    SymbolSelector,
)


BENCHMARK_SEED = 20_260_723
DEFAULT_NODE_COUNT = 10_000
DEFAULT_REQUEST_COUNT = 200
DEFAULT_WARMUPS = 20
THRESHOLD_MS = 1_000.0


def build_reference_graph(
    node_count: int = DEFAULT_NODE_COUNT,
    *,
    seed: int = BENCHMARK_SEED,
) -> CodeGraph:
    """Build fixed disconnected cyclic components with four edges per node."""

    if node_count < 8:
        raise ValueError("node_count must be at least 8")
    generator = Random(seed)
    graph = CodeGraph(
        {
            "source_fingerprint": f"benchmark-seed-{seed}-nodes-{node_count}",
            "benchmark_seed": seed,
        }
    )
    component_size = max(8, node_count // 4)
    for index in range(node_count):
        ambiguous = index % max(2, node_count // 20) == 0
        name = "AmbiguousSymbol" if ambiguous else f"Node{index:05d}"
        node = GraphNode(
            id=f"node:{index:05d}",
            kind="function" if index % 7 else "method",
            name=name,
            qualified_name=f"Component{index // component_size}::{name}::{index:05d}",
            location=SourceLocation(
                f"Component{index // component_size}.mq5",
                index % 400 + 1,
                index % 80 + 1,
            ),
            attributes={"benchmark_index": index},
        )
        graph.nodes[node.id] = node

    offsets = (1, 7, 31, 73)
    origins = ("extracted", "resolved", "runtime", "inferred")
    relationships = ("calls", "references", "runtime_dispatches", "may_trigger_event")
    for source_index in range(node_count):
        component_start = (source_index // component_size) * component_size
        component_end = min(component_start + component_size, node_count)
        component_length = component_end - component_start
        local_index = source_index - component_start
        for slot, offset in enumerate(offsets):
            target_index = component_start + ((local_index + offset) % component_length)
            confidence = (10_000 - ((source_index * 37 + slot * 997) % 5_001)) / 10_000
            edge = GraphEdge(
                id=f"edge:{source_index:05d}:{slot}",
                source=f"node:{source_index:05d}",
                target=f"node:{target_index:05d}",
                relationship=relationships[slot],
                origin=origins[slot],
                confidence=confidence,
                location=SourceLocation(
                    f"Component{source_index // component_size}.mq5",
                    source_index % 400 + 1,
                    slot + 1,
                ),
                attributes={"benchmark_slot": slot},
            )
            graph.edges[edge.id] = edge

    diagnostic_count = max(4, node_count // 100)
    for index in range(diagnostic_count):
        graph.diagnostics.append(
            Diagnostic(
                code=f"BENCH{index % 7:03d}",
                severity=("error", "warning", "info")[index % 3],
                message=f"Synthetic benchmark diagnostic {generator.randrange(10_000)}",
                location=SourceLocation(
                    f"Component{index % 4}.mq5",
                    index % 400 + 1,
                    1,
                ),
            )
        )
    return graph


def build_request_mix(
    node_count: int,
    request_count: int = DEFAULT_REQUEST_COUNT,
    *,
    seed: int = BENCHMARK_SEED,
) -> tuple[IntelligenceRequest, ...]:
    """Return a fixed balanced request mix for four bounded operations."""

    generator = Random(seed)
    component_size = max(8, node_count // 4)
    requests: list[IntelligenceRequest] = []
    operations = ("query", "context", "path", "context_package")
    for index in range(request_count):
        source_index = generator.randrange(node_count)
        component_start = (source_index // component_size) * component_size
        component_end = min(component_start + component_size, node_count)
        target_index = component_start + (
            (source_index - component_start + 7) % (component_end - component_start)
        )
        operation = operations[index % len(operations)]
        if operation == "query":
            request = IntelligenceRequest(
                operation=operation,
                targets=(SymbolSelector(f"node:{source_index:05d}"),),
                bounds=IntelligenceBounds(max_items=5),
            )
        elif operation == "context":
            request = IntelligenceRequest(
                operation=operation,
                targets=(SymbolSelector(f"node:{source_index:05d}"),),
                direction="both",
                bounds=IntelligenceBounds(max_depth=1, max_items=20),
            )
        elif operation == "path":
            request = IntelligenceRequest(
                operation=operation,
                targets=(
                    SymbolSelector(f"node:{source_index:05d}"),
                    SymbolSelector(f"node:{target_index:05d}"),
                ),
                direction="outgoing",
                bounds=IntelligenceBounds(
                    max_depth=2,
                    max_paths=3,
                    max_expansions=200,
                ),
            )
        else:
            request = IntelligenceRequest(
                operation=operation,
                targets=(SymbolSelector(f"node:{source_index:05d}"),),
                direction="both",
                bounds=IntelligenceBounds(
                    max_depth=1,
                    max_expansions=200,
                    context_units=20,
                ),
            )
        requests.append(request)
    return tuple(requests)


def _nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(percentile * len(ordered) + 0.999999) - 1))
    return ordered[index]


def _timing_summary(values: list[float]) -> dict[str, float | int]:
    return {
        "count": len(values),
        "p50_ms": round(float(median(values)), 6),
        "p95_ms": round(_nearest_rank(values, 0.95), 6),
        "max_ms": round(max(values), 6),
    }


def _validate_response(operation: str, result) -> None:
    payload = result.to_dict()
    if payload["operation"] != operation:
        raise AssertionError("response operation mismatch")
    if payload["completion"]["explored_nodes"] < 0:
        raise AssertionError("negative explored node count")
    if operation == "path":
        for path in payload["paths"]:
            if len(path["node_ids"]) != len(path["hops"]) + 1:
                raise AssertionError("non-contiguous path envelope")
            for hop in path["hops"]:
                if hop["evidence"]["origin"] not in {
                    "extracted",
                    "resolved",
                    "runtime",
                    "inferred",
                }:
                    raise AssertionError("unsupported path evidence origin")
    if operation == "context_package":
        package = payload["context_package"]
        if package["budget_used"] > package["budget_limit"]:
            raise AssertionError("context budget exceeded")
        node_ids = {
            item["subject_id"]
            for item in package["items"]
            if item["category"] in {"target", "node"}
        }
        for item in package["items"]:
            if item["category"] == "relationship":
                if (
                    item["summary"]["source"] not in node_ids
                    or item["summary"]["target"] not in node_ids
                ):
                    raise AssertionError("non-atomic relationship group")


def run_benchmark(
    *,
    node_count: int = DEFAULT_NODE_COUNT,
    request_count: int = DEFAULT_REQUEST_COUNT,
    warmups: int = DEFAULT_WARMUPS,
    seed: int = BENCHMARK_SEED,
    enforce_timing: bool = False,
) -> dict[str, Any]:
    """Build, validate, time, and report one deterministic benchmark run."""

    graph = build_reference_graph(node_count, seed=seed)
    graph_before = sha256(graph.to_json().encode("utf-8")).hexdigest()
    index_started = perf_counter_ns()
    kernel = IntelligenceKernel(graph)
    index_build_ns = perf_counter_ns() - index_started
    requests = build_request_mix(node_count, request_count, seed=seed)
    for request in requests[:warmups]:
        _validate_response(request.operation, kernel.execute(request))

    timings: dict[str, list[float]] = defaultdict(list)
    all_timings: list[float] = []
    validated = 0
    for request in requests:
        started = perf_counter_ns()
        result = kernel.execute(request)
        elapsed_ms = (perf_counter_ns() - started) / 1_000_000
        _validate_response(request.operation, result)
        timings[request.operation].append(elapsed_ms)
        all_timings.append(elapsed_ms)
        validated += 1

    graph_after = sha256(graph.to_json().encode("utf-8")).hexdigest()
    overall = _timing_summary(all_timings)
    threshold_passed = overall["p95_ms"] < THRESHOLD_MS
    if enforce_timing and not threshold_passed:
        raise AssertionError(
            f"p95 {overall['p95_ms']} ms exceeds {THRESHOLD_MS} ms"
        )
    return {
        "schema_version": 1,
        "enabled": True,
        "seed": seed,
        "environment": {
            "python": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "os": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logical_cpu_count": os.cpu_count(),
            "power_profile_note": os.environ.get(
                "MQL5_CODEGRAPH_POWER_PROFILE",
                "not_recorded",
            ),
        },
        "graph": {
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "diagnostics": len(graph.diagnostics),
        },
        "index_build_ns": index_build_ns,
        "warmups": warmups,
        "requests": request_count,
        "operations": {
            operation: _timing_summary(values)
            for operation, values in sorted(timings.items())
        },
        "overall": overall,
        "threshold_ms": THRESHOLD_MS,
        "threshold_passed": threshold_passed,
        "timing_enforced": enforce_timing,
        "validation": {
            "responses": validated,
            "graph_unchanged": graph_before == graph_after,
        },
    }


def main() -> int:
    enabled = os.environ.get("MQL5_CODEGRAPH_PERF") == "1"
    if not enabled:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "enabled": False,
                    "message": "Set MQL5_CODEGRAPH_PERF=1 to run the 10k benchmark",
                },
                sort_keys=True,
            )
        )
        return 0
    report = run_benchmark(enforce_timing=True)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
