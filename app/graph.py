"""Deterministic graph operations for small operational context graphs."""
from collections import deque


class GraphError(ValueError):
    """Raised when an input graph or query is invalid."""


def validate_graph(graph):
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise GraphError("Graph must contain nodes and edges arrays")
    ids = [node.get("id") for node in nodes if isinstance(node, dict)]
    if len(ids) != len(nodes) or any(not isinstance(value, str) or not value for value in ids):
        raise GraphError("Every node requires a nonempty string id")
    if len(ids) != len(set(ids)):
        raise GraphError("Duplicate node id")
    known = set(ids)
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("source") not in known or edge.get("target") not in known:
            raise GraphError("Edge references unknown node")
    return graph


def shortest_path(graph, source, target):
    """Return an undirected shortest explanation path as node ids, or []."""
    validate_graph(graph)
    known = {node["id"] for node in graph["nodes"]}
    if source not in known or target not in known:
        raise GraphError("Unknown source or target node")
    neighbors = {node_id: set() for node_id in known}
    for edge in graph["edges"]:
        neighbors[edge["source"]].add(edge["target"])
        neighbors[edge["target"]].add(edge["source"])
    queue = deque([source])
    previous = {source: None}
    while queue:
        current = queue.popleft()
        if current == target:
            path = []
            while current is not None:
                path.append(current)
                current = previous[current]
            return path[::-1]
        for neighbor in sorted(neighbors[current]):
            if neighbor not in previous:
                previous[neighbor] = current
                queue.append(neighbor)
    return []


def neighborhood(graph, node_id, hops=1):
    """Return induced subgraph within hops, treating relationships as navigable in both directions."""
    validate_graph(graph)
    if not isinstance(hops, int) or not 0 <= hops <= 4:
        raise GraphError("hops must be an integer between 0 and 4")
    if node_id not in {node["id"] for node in graph["nodes"]}:
        raise GraphError("Unknown node")
    selected = {node_id}
    for _ in range(hops):
        selected |= {v for e in graph["edges"] for u, v in ((e["source"], e["target"]), (e["target"], e["source"])) if u in selected}
    return {"nodes": [n for n in graph["nodes"] if n["id"] in selected], "edges": [e for e in graph["edges"] if e["source"] in selected and e["target"] in selected]}
