
"""Integration tests for the ContextOps HTTP API."""

from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from urllib.request import urlopen
import json

import pytest

from http.server import ThreadingHTTPServer
from app.server import Handler


@pytest.fixture
def running_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
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
            assert "tasks" in response
        else:
            assert response["task_id"] == "test-001"
            assert "findings" in response
            assert "graph" in response
