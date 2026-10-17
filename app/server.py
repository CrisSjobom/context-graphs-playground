"""Minimal HTTP service. No third-party runtime dependencies."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import mimetypes
import os

from app.graph import GraphError, shortest_path, neighborhood, validate_graph
from app.operations import DomainError, connect, ingest, evaluate, operational_graph

ROOT = Path(__file__).resolve().parent.parent
GRAPH = validate_graph(json.loads((ROOT / "data" / "scenario.json").read_text(encoding="utf-8")))
PUBLIC = ROOT / "web"
DB = connect(os.environ.get("CONTEXTOPS_DB", str(ROOT / "contextops.sqlite")))


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
        self.send_bytes(json.dumps(value, ensure_ascii=False).encode("utf-8"), status=status)

    def do_POST(self):
        if urlparse(self.path).path != "/api/events":
            return self.json({"error": "Not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                return self.json({"error": "Body must be between 1 and 65536 bytes"}, 413)
            payload = json.loads(self.rfile.read(length))
            inserted = ingest(DB, payload)
            return self.json({"inserted": inserted, "event_id": payload["event_id"]}, 201 if inserted else 200)
        except (DomainError, ValueError, KeyError, json.JSONDecodeError) as exc:
            return self.json({"error": str(exc)}, 400)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path == "/api/tasks":
            rows = DB.execute("SELECT DISTINCT task_id FROM events ORDER BY task_id").fetchall()
            return self.json({"tasks": [row[0] for row in rows]})
        if parsed.path == "/api/investigate":
            task_id = params.get("task_id", [""])[0]
            if not task_id:
                return self.json({"error": "task_id is required"}, 400)
            report = evaluate(DB, task_id)
            return self.json({**report, "graph": operational_graph(report)})
        if parsed.path == "/api/graph":
            return self.json(GRAPH)
        if parsed.path == "/api/health":
            return self.json({"status": "ok"})
        try:
            if parsed.path == "/api/path":
                return self.json({"path": shortest_path(GRAPH, params.get("from", [""])[0], params.get("to", [""])[0])})
            if parsed.path == "/api/neighborhood":
                hops = int(params.get("hops", ["1"])[0])
                return self.json(neighborhood(GRAPH, params.get("id", [""])[0], hops))
        except (GraphError, ValueError) as exc:
            return self.json({"error": str(exc)}, status=400)
        # Restrict static responses to explicit known files; no arbitrary file reads.
        assets = {"/": "index.html", "/index.html": "index.html", "/styles.css": "styles.css", "/app.js": "app.js", "/favicon.svg": "favicon.svg", "/operations.html": "operations.html"}
        if parsed.path not in assets:
            return self.json({"error": "Not found"}, status=404)
        path = PUBLIC / assets[parsed.path]
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return self.send_bytes(path.read_bytes(), mime)


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Context Graphs Playground → http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
