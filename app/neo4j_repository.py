
"""Neo4j graph projection for operational investigations."""

from neo4j import GraphDatabase


class Neo4jRepository:
    """Persist a derived operational graph without changing the event journal."""

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        self.driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
        )
        self.database = database

    def close(self):
        self.driver.close()

    def verify_connection(self):
        self.driver.verify_connectivity()

    def sync_graph(self, graph: dict):
        """Upsert nodes and relationships using stable IDs."""
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        node_ids = {node["id"] for node in nodes}

        for edge in edges:
            if edge["source"] not in node_ids or edge["target"] not in node_ids:
                raise ValueError("Relationship references an unknown node")

        with self.driver.session(database=self.database) as session:
            session.execute_write(self._write_graph, nodes, edges)

        return {
            "nodes_synced": len(nodes),
            "relationships_synced": len(edges),
        }

    @staticmethod
    def _write_graph(tx, nodes, edges):
        tx.run(
            """
            UNWIND $nodes AS node
            MERGE (n:ContextNode {id: node.id})
            SET n.label = node.label,
                n.type = node.type,
                n.time = node.time
            """,
            nodes=[
                {
                    "id": node["id"],
                    "label": node.get("label", ""),
                    "type": node.get("type", ""),
                    "time": node.get("time"),
                }
                for node in nodes
            ],
        ).consume()

        tx.run(
            """
            UNWIND $edges AS edge
            MATCH (source:ContextNode {id: edge.source})
            MATCH (target:ContextNode {id: edge.target})
            MERGE (source)-[r:CONTEXT_RELATION {
                kind: edge.label
            }]->(target)
            """,
            edges=edges,
        ).consume()
