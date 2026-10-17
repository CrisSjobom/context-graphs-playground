import pytest

from context_graphs.data import demo_graph
from context_graphs.model import Edge, Graph, Node


def test_trace_returns_root_and_provenance():
    result = demo_graph().trace("incident-1042", depth=2)
    assert result["results"][0]["node"].id == "incident-1042"
    decision = next(r for r in result["results"] if r["node"].id == "decision-06")
    assert decision["path"][0]["relation"] == "RESOLVED_THROUGH"


def test_depth_zero_only_returns_root():
    assert len(demo_graph().trace("incident-1042", depth=0)["results"]) == 1


def test_missing_node_raises():
    with pytest.raises(KeyError):
        demo_graph().trace("missing")


def test_invalid_depth_rejected():
    with pytest.raises(ValueError):
        demo_graph().trace("incident-1042", depth=-1)


def test_dangling_edge_rejected():
    with pytest.raises(ValueError, match="Dangling edge"):
        Graph([Node("one", "test", "One")], [Edge("one", "two", "INVALID")])


def test_duplicate_ids_rejected():
    with pytest.raises(ValueError, match="unique"):
        Graph([Node("one", "test", "One"), Node("one", "test", "Two")], [])
