
"""HTTP integration tests with isolated SQLite storage."""

from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen
import json

import pytest

import app.server as server_module
from app.operations import connect


@pytest.fixture
def running_server(tmp_path, monkeypatch):
    """Run the HTTP server against an isolated temporary database."""
    db_path = tmp_path / "contextops-test.sqlite"

    # Redirect database operations without changing the developer's data.
    monkeypatch.setattr(server_module, "DB_PATH", db_path)

    db = connect(db_path)
    db.close()

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        server_module.Handler,
    )

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request_json(url):
    with urlopen(url, timeout=5) as response:
        return json.load(response)


def test_health_endpoint(running_server):
    response = request_json(f"{running_server}/api/health")
    assert response == {"status": "ok"}


def test_concurrent_database_requests(running_server):
    """Database reads must succeed across HTTP worker threads."""
    urls = [
        f"{running_server}/api/tasks",
        f"{running_server}/api/investigate?task_id=test-001",
    ] * 10

    with ThreadPoolExecutor(max_workers=5) as executor:
        responses = list(executor.map(request_json, urls))

    assert len(responses) == 20

    for index, response in enumerate(responses):
        if index % 2 == 0:
            assert response == {"tasks": []}
        else:
            assert response["task_id"] == "test-001"
            assert response["event_count"] == 0
            assert response["findings"] == []
            assert "graph" in response
