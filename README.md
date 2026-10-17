# Context Graphs Playground

**Make operational decisions traceable.**

A small reference implementation for investigating logistics incidents through a directed context graph. Instead of reducing an incident to a ticket status, the graph connects the affected job, operational events, assigned resources, governing policy, and the decision taken.

> **Scope:** An independent learning project using fictional operations, identifiers, and event data. It does not connect to or reproduce any employer's production systems.

## Why this exists

Operational systems usually record facts in separate places. A job service knows the assignment, an event stream captures the timeline, and a support workflow records the resolution. Reconstructing the reasoning behind a decision can be harder than retrieving the decision itself.

This playground models those connections explicitly and preserves a path from an incident to the supporting context. It is an exploration of a design question: **How can we make an operational decision easier to inspect, explain, and challenge?**

## What it does

- Models incidents, jobs, couriers, vehicles, zones, policies, events, and decisions as typed nodes.
- Encodes directed, named relationships such as `TRIGGERED_BY` and `GOVERNED_BY`.
- Traces related nodes using breadth-first traversal, returning explicit relation paths.
- Exports a standalone, interactive HTML graph with a node inspector and no server requirement.
- Rejects duplicate node IDs, dangling references, and invalid traversal depths.

## Quick start

Requires Python 3.10+.

```bash
python -m pip install -e .
context-graphs trace incident-1042 --depth 2
context-graphs export --output graph.html
```

Open `graph.html` in a browser. You can also try a ready-made preview in [`demo.html`](demo.html).

## Example question

**Why was pickup #314 reassigned?**

The synthetic graph contains an open incident, a missing location update, and a subsequent reassignment decision governed by a late-pickup escalation policy. Run the trace to inspect which relationships link these records. The output is a graph traversal, **not** an automated causal inference or a recommendation engine.

## Design notes

| Decision | Rationale | Trade-off |
| --- | --- | --- |
| Directed graph | Preserves relationship semantics | Reverse exploration requires another traversal strategy |
| In-memory model | Keeps the core transparent and easy to test | Not suitable for large datasets |
| Explicit evidence paths | Supports inspection and audit-style exploration | The path alone does not prove causality |
| Static HTML export | Works locally without infrastructure | The generated view is a snapshot |

See [architecture](docs/architecture.md) for model boundaries and possible next steps.

## Repository layout

```text
src/context_graphs/  graph model, synthetic fixture, traversal, and HTML export
tests/               validation and traversal tests
docs/                architectural decisions and limitations
demo.html            standalone interactive graph preview
```

## Quality checks

```bash
python -m pip install -e '.[dev]'
pytest -q
ruff check .
```

## Roadmap

- [ ] Timeline-aware traversal and event ordering
- [ ] Query predicates by relationship and node type
- [ ] Optional Neo4j adapter and Cypher query examples
- [ ] Human-readable explanation report with provenance
- [ ] Larger synthetic scenarios and performance profiling

## License

MIT. Designed as a learning artifact, not a production operations platform.
