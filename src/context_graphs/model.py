"""Typed graph primitives and validation for operational context."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    label: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    relation: str


class Graph:
    def __init__(self, nodes: list[Node], edges: list[Edge]):
        self.nodes = {node.id: node for node in nodes}
        if len(self.nodes) != len(nodes):
            raise ValueError("Node IDs must be unique")
        self.edges = edges
        for edge in edges:
            if edge.source not in self.nodes or edge.target not in self.nodes:
                raise ValueError(f"Dangling edge: {edge.source} -> {edge.target}")

    def neighbors(self, node_id: str) -> list[tuple[Edge, Node]]:
        if node_id not in self.nodes:
            raise KeyError(node_id)
        return [(edge, self.nodes[edge.target]) for edge in self.edges if edge.source == node_id]

    def trace(self, start: str, depth: int = 3) -> dict[str, Any]:
        """Breadth-first directed traversal with explicit evidence paths."""
        if start not in self.nodes:
            raise KeyError(start)
        if depth < 0:
            raise ValueError("depth must be non-negative")
        queue: list[tuple[str, list[dict[str, str]]]] = [(start, [])]
        visited = {start}
        results = []
        index = 0
        while index < len(queue):
            node_id, path = queue[index]
            index += 1
            results.append({"node": self.nodes[node_id], "path": path})
            if len(path) >= depth:
                continue
            for edge, target in self.neighbors(node_id):
                if target.id in visited:
                    continue
                visited.add(target.id)
                queue.append((target.id, path + [{"from": edge.source, "relation": edge.relation, "to": edge.target}]))
        return {"root": start, "depth": depth, "results": results}
