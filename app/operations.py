"""Event-sourced operational state and explainable, deterministic policy checks.

SQLite is the local durable journal. These checks are rules, not AI inference.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

EVENT_TYPES = {"task_created", "driver_confirmed", "payment_settled", "custody_verified", "task_closed"}


class DomainError(ValueError):
    pass


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    db = sqlite3.connect(str(path))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("""CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, event_type TEXT NOT NULL,
        occurred_at TEXT NOT NULL, source TEXT NOT NULL, payload TEXT NOT NULL,
        ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS events_by_task ON events(task_id, occurred_at, event_id)")
    db.commit()
    return db


def ingest(db: sqlite3.Connection, event: dict[str, Any]) -> bool:
    """Insert once by external event ID; conflicting replays are rejected."""
    required = ("event_id", "task_id", "event_type", "occurred_at", "source")
    if not isinstance(event, dict) or any(not isinstance(event.get(k), str) or not event[k].strip() for k in required):
        raise DomainError("event_id, task_id, event_type, occurred_at and source are required strings")
    if event["event_type"] not in EVENT_TYPES:
        raise DomainError("Unsupported event_type")
    try:
        instant = datetime.fromisoformat(event["occurred_at"].replace("Z", "+00:00"))
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("Timezone required")
    except ValueError as exc:
        raise DomainError("occurred_at must be timezone-aware ISO 8601") from exc
    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        raise DomainError("payload must be an object")
    record = (event["event_id"], event["task_id"], event["event_type"], instant.isoformat(), event["source"], json.dumps(payload, sort_keys=True))
    old = db.execute("SELECT * FROM events WHERE event_id=?", (event["event_id"],)).fetchone()
    if old:
        if tuple(old[k] for k in ("event_id", "task_id", "event_type", "occurred_at", "source", "payload")) == record:
            return False
        raise DomainError("event_id already exists with different content")
    with db:
        db.execute("INSERT INTO events(event_id,task_id,event_type,occurred_at,source,payload) VALUES (?,?,?,?,?,?)", record)
    return True


def history(db: sqlite3.Connection, task_id: str) -> list[dict[str, Any]]:
    rows = db.execute("SELECT * FROM events WHERE task_id=? ORDER BY occurred_at,event_id", (task_id,)).fetchall()
    return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]


def evaluate(db: sqlite3.Connection, task_id: str) -> dict[str, Any]:
    """Reconstruct state by event-time; return findings linked to event IDs."""
    events = history(db, task_id)
    state = {"created": False, "driver_confirmed": False, "payment_settled": False,
             "custody_verified": False, "closed": False}
    evidence: dict[str, str] = {}
    findings = []
    for event in events:
        event_type = event["event_type"]
        state_key = {"task_created": "created", "driver_confirmed": "driver_confirmed",
                     "payment_settled": "payment_settled", "custody_verified": "custody_verified",
                     "task_closed": "closed"}[event_type]
        state[state_key] = True
        evidence[state_key] = event["event_id"]
        if event_type == "task_closed" and not state["custody_verified"]:
            findings.append({"rule_id": "CUSTODY_BEFORE_CLOSURE", "severity": "high",
                "description": "Task closed without prior verified custody transfer",
                "evidence_event_ids": [event["event_id"]] + ([evidence["driver_confirmed"]] if state["driver_confirmed"] else []),
                "detected_at": event["occurred_at"]})
        if event_type == "payment_settled" and not state["custody_verified"]:
            findings.append({"rule_id": "PAYMENT_WITHOUT_CUSTODY", "severity": "medium",
                "description": "Payment settled before physical custody was verified",
                "evidence_event_ids": [event["event_id"]], "detected_at": event["occurred_at"]})
    return {"task_id": task_id, "event_count": len(events), "state": state,
            "findings": findings, "evidence": events}


def operational_graph(report: dict[str, Any]) -> dict[str, Any]:
    """Generate a directed graph with traceable event and policy relationships."""
    task = report["task_id"]
    nodes = [{"id": f"task:{task}", "label": task, "type": "task"}]
    edges = []
    for event in report["evidence"]:
        eid = f"event:{event['event_id']}"
        nodes.append({"id": eid, "label": event["event_type"], "type": "event", "time": event["occurred_at"]})
        edges.append({"source": f"task:{task}", "target": eid, "label": "HAS_EVENT"})
    for i, finding in enumerate(report["findings"]):
        fid = f"finding:{i}"
        nodes.append({"id": fid, "label": finding["rule_id"], "type": "finding"})
        edges.extend({"source": fid, "target": f"event:{eid}", "label": "SUPPORTED_BY"} for eid in finding["evidence_event_ids"])
    return {"nodes": nodes, "edges": edges}
