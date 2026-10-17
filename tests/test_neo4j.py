
"""Unit tests for the Neo4j graph repository."""

from unittest.mock import MagicMock, patch

import pytest

from app.neo4j_repository import Neo4jRepository


@pytest.fixture
def repository():
    """Create a repository with a mocked Neo4j driver."""
    with patch("app.neo4j_repository.GraphDatabase.driver") as driver:
        repo = Neo4jRepository(
            uri="bolt://localhost:7687",
            user="test",
            password="test",
        )
        yield repo, driver.return_value
        repo.close()


@pytest.fixture
def sample_graph():
    return {
        "nodes": [
            {"id": "task:001", "label": "Task 001", "type": "task"},
            {
                "id": "event:001",
                "label": "task_created",
                "type": "event",
            },
        ],
        "edges": [
            {
                "source": "task:001",
                "target": "event:001",
                "label": "HAS_EVENT",
            }
        ],
    }


def test_repository_initializes_driver(repository):
    repo, driver = repository

    assert repo.database == "neo4j"
    assert driver is not None


def test_rejects_unknown_relationship_nodes(repository, sample_graph):
    repo, driver = repository

    sample_graph["edges"][0]["target"] = "event:missing"

    with pytest.raises(ValueError, match="unknown node"):
        repo.sync_graph(sample_graph)

    driver.session.assert_not_called()


def test_sync_uses_write_transaction(repository, sample_graph):
    repo, driver = repository

    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session

    result = repo.sync_graph(sample_graph)

    assert result == {
        "nodes_synced": 2,
        "relationships_synced": 1,
    }

    session.execute_write.assert_called_once()


def test_write_graph_generates_merge_queries(sample_graph):
    """Projection uses MERGE for repeatable upserts."""
    tx = MagicMock()

    Neo4jRepository._write_graph(
        tx,
        sample_graph["nodes"],
        sample_graph["edges"],
    )

    assert tx.run.call_count == 2

    node_query = tx.run.call_args_list[0].args[0]
    relationship_query = tx.run.call_args_list[1].args[0]

    assert "MERGE (n:ContextNode" in node_query
    assert "MERGE (source)-[r:CONTEXT_RELATION" in relationship_query
