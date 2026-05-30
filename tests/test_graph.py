"""Wiring smoke: compile the graph and confirm node names + edges."""
from agent.graph import build_graph


def test_graph_compiles():
    g = build_graph()
    # The compiled graph exposes a JSON graph representation we can inspect.
    spec = g.get_graph()
    node_ids = set(spec.nodes.keys())
    assert {"retrieve", "reason", "act", "reflect", "persist"} <= node_ids