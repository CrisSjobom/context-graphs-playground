"""Command-line interface."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .data import demo_graph
from .export import render_html


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Explore a synthetic operational context graph")
    sub = parser.add_subparsers(dest="command", required=True)
    trace = sub.add_parser("trace", help="Trace a node and show evidence paths as JSON")
    trace.add_argument("node", nargs="?", default="incident-1042")
    trace.add_argument("--depth", type=int, default=3)
    export = sub.add_parser("export", help="Generate a standalone interactive HTML graph")
    export.add_argument("--output", type=Path, default=Path("graph.html"))
    args = parser.parse_args(argv)
    graph = demo_graph()
    if args.command == "trace":
        result = graph.trace(args.node, args.depth)
        result["results"] = [{"node": asdict(r["node"]), "path": r["path"]} for r in result["results"]]
        print(json.dumps(result, indent=2))
    else:
        render_html(graph, args.output)
        print(f"Generated {args.output}")


if __name__ == "__main__":
    main()
