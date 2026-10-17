
"""HTTP service for operational investigations and context graph exploration.

Uses one SQLite connection per database operation to keep request handling
safe across the threads managed by ThreadingHTTPServer.
No third-party runtime dependencies.
"""

import json
import mimetypes
import os
import sqlite3
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.graph import GraphError, neighborhood, shortest_path, validate_graph
from app.operations import DomainError, connect, evaluate, ingest, operational_graph

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "web"
DB_PATH = Path(
    os.environ.get("CONTEXTOPS_DB", str(ROOT / "contextops.sqlite"))
)

GRAPH = validate_graph(
    json.loads((ROOT / "data" / "scenario.json").read_text(encoding="utf-8"))
)

# Initialize the database schema, then release the connection.
with_db = connect(DB_PATH)
with_db.close()


@contextmanager
def database():
    """Open a SQLite connection for the current operation."""
    db = connect(DB_PATH)
    try:
        yield db
    finally:
        db.close()


class Handler(BaseHTTPRequestHandler):

    def send_bytes(self, data, content_type="application/json", status=200):
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def json(self, value, status=200):
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_bytes(payload, status=status)

    def do_POST(self):
        if urlparse(self.path).path != "/api/events":
            return self.json({"error": "Not found"}, 404)

        try:
            length = int(self.headers.get("Content-Length", "0"))

            if not 0 < length <= 65536:
                return self.json(
                    {"error": "Body must be between 1 and 65536 bytes"}, 413
                )

            payload = json.loads(self.rfile.read(length))

            with database() as db:
                inserted = ingest(db, payload)

            return self.json(
                {"inserted": inserted, "event_id": payload["event_id"]},
                201 if inserted else 200,
            )

        except (DomainError, ValueError, KeyError, TypeError) as exc:
            return self.json({"error": str(exc)}, 400)

        except sqlite3.Error:
            self.log_error("Database error while ingesting event")
            return self.json({"error": "Database operation failed"}, 500)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        try:
            return self.handle_get(parsed.path, params)

        except (GraphError, ValueError) as exc:
            return self.json({"error": str(exc)}, 400)

        except sqlite3.Error:
            self.log_error("Database error while processing request")
            return self.json({"error": "Database operation failed"}, 500)

    def handle_get(self, path, params):
        if path == "/api/health":
            return self.json({"status": "ok"})

        if path == "/api/tasks":
            with database() as db:
                rows = db.execute(
                    "SELECT DISTINCT task_id FROM events ORDER BY task_id"
                ).fetchall()

            return self.json({"tasks": [row[0] for row in rows]})

        if path == "/api/investigate":
            task_id = params.get("task_id", [""])[0]

            if not task_id:
                return self.json({"error": "task_id is required"}, 400)

            with database() as db:
                report = evaluate(db, task_id)

            return self.json({
                **report,
                "graph": operational_graph(report),
            })

        if path == "/api/graph":
            return self.json(GRAPH)

        if path == "/api/path":
            return self.json({
                "path": shortest_path(
                    GRAPH,
                    params.get("from", [""])[0],
                    params.get("to", [""])[0],
                )
            })

        if path == "/api/neighborhood":
            hops = int(params.get("hops", ["1"])[0])
            return self.json(
                neighborhood(
                    GRAPH,
                    params.get("id", [""])[0],
                    hops,
                )
            )

        assets = {
            "/": "index.html",
            "/index.html": "index.html",
            "/styles.css": "styles.css",
            "/app.js": "app.js",
            "/favicon.svg": "favicon.svg",
            "/operations.html": "operations.html",
            "/graph-explorer.js": "graph-explorer.js",
        }

        if path not in assets:
            return self.json({"error": "Not found"}, 404)

        file_path = PUBLIC / assets[path]

        if not file_path.is_file():
            return self.json({"error": "Asset not found"}, 404)

        mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        return self.send_bytes(file_path.read_bytes(), mime)


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))

    server = ThreadingHTTPServer((host, port), Handler)

    print(f"ContextOps → http://{host}:{port}", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping ContextOps...")
    finally:
        server.server_close()
