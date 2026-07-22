"""MQL5 terminal event and trading lifecycle enrichment."""

from __future__ import annotations

from .graph import CodeGraph, GraphNode, stable_id


def enrich_runtime(graph: CodeGraph) -> None:
    terminal = graph.add_node(GraphNode(
        id=stable_id("runtime", "MetaTrader5Terminal"), kind="runtime",
        name="MetaTrader 5 Terminal", qualified_name="runtime::MetaTrader5Terminal",
        attributes={"platform": "MetaTrader 5"},
    ))
    handlers: dict[str, list[GraphNode]] = {}
    for node in list(graph.nodes.values()):
        if node.kind != "event_handler":
            continue
        handlers.setdefault(node.name, []).append(node)
        graph.add_edge(terminal.id, node.id, "runtime_dispatches", "runtime", 1.0,
                       node.location, {"event": node.name})

    transaction_handlers = handlers.get("OnTradeTransaction", [])
    if transaction_handlers:
        send_nodes = [node for node in graph.nodes.values()
                      if node.kind == "external_function" and node.name in {"OrderSend", "OrderSendAsync"}]
        for send_node in send_nodes:
            for handler in transaction_handlers:
                graph.add_edge(send_node.id, handler.id, "may_trigger_event", "runtime", 0.9,
                               attributes={"runtime_rule": "trade request processing"})

    timer_handlers = handlers.get("OnTimer", [])
    timer_nodes = [node for node in graph.nodes.values()
                   if node.kind == "external_function" and node.name in {"EventSetTimer", "EventSetMillisecondTimer"}]
    for timer_node in timer_nodes:
        for handler in timer_handlers:
            graph.add_edge(timer_node.id, handler.id, "may_trigger_event", "runtime", 0.95,
                           attributes={"runtime_rule": "timer registration"})
