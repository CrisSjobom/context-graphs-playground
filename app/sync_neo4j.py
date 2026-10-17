"""Synchronize an operational investigation from SQLite to Neo4j."""

import os
from pathlib import Path

from app.operations import connect, evaluate, operational_graph
from app.neo4j_repository import Neo4jRepository


def load_env(path=".env"):
    """Load local environment variables without external dependencies."""
    env_file = Path(path)
    if not env_file.exists():
        return

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator:
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main():
    load_env()

    task_id = "pickup-314"
    db_path = os.getenv("CONTEXTOPS_DB", "contextops.sqlite")

    db = connect(db_path)
    try:
        report = evaluate(db, task_id)
    finally:
        db.close()

    if not report["event_count"]:
        print(f"No events found for {task_id}. Nothing synchronized.")
        return

    graph = operational_graph(report)

    repository = Neo4jRepository(
        uri=os.environ["NEO4J_URI"],
        user=os.environ["NEO4J_USER"],
        password=os.environ["NEO4J_PASSWORD"],
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )

    try:
        repository.verify_connection()
        result = repository.sync_graph(graph)
        print(f"Task: {task_id}")
        print(f"Events: {report['event_count']}")
        print(f"Findings: {len(report['findings'])}")
        print(f"Neo4j sync: {result}")
    finally:
        repository.close()


if __name__ == "__main__":
    main()
