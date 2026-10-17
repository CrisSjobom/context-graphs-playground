# Architecture and boundaries

## Domain model

`Node` holds an immutable identity, type, label, and a small bag of attributes. `Edge` is a directed, named relation between two node IDs. `Graph` validates referential integrity during construction.

The example represents a delayed vehicle pickup. The graph has no external storage or data ingestion by design: sample data lives in `data.py`, separated from the graph algorithms.

## Evidence tracing

`Graph.trace(root, depth)` uses a breadth-first traversal with a visited set. Each result includes the concrete edge sequence taken from the root. This is a shortest *hop-count* path in the directed graph. It is not a causal model or a statistical confidence measure. Where multiple shortest routes lead to the same node, the first encountered route is retained.

Complexity is `O(V + E)` in the worst case for reachable nodes and edges, excluding path materialization. The current `neighbors` implementation scans the full edge list for each visited node: it favors clarity over scale and should be replaced with an adjacency index for larger graphs.

## Security and privacy

The fixture uses synthetic data only. The HTML exporter escapes node labels and attribute JSON before embedding in HTML. The UI shows attributes via `textContent`, not `innerHTML`. A production version would need authorization, sensitive-data minimization, retention policies, event freshness guarantees, and audit logging.

## What is deliberately out of scope

No LLM, RAG, Neo4j, live integrations, routing optimizer, or causal inference engine is implemented in this version. These are optional extensions rather than implied capabilities.

## Next architectural experiment

Persist the same model in Neo4j, retain relationship semantics, and compare traversal queries across in-memory and Cypher implementations. Add source metadata and event timestamps to each relationship before generating narrated explanations.
