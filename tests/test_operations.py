import pytest

from app.operations import DomainError, connect, evaluate, history, ingest, operational_graph


def evt(id, typ, minute, task="T-1"):
    return {"event_id": id, "task_id": task, "event_type": typ,
            "occurred_at": f"2026-10-01T10:{minute:02d}:00+00:00", "source": "simulation", "payload": {}}


def test_out_of_order_ingestion_replays_by_event_time():
    db = connect()
    ingest(db, evt("close", "task_closed", 15))
    ingest(db, evt("verified", "custody_verified", 12))
    assert evaluate(db, "T-1")["findings"] == []
    assert [e["event_id"] for e in history(db, "T-1")] == ["verified", "close"]


def test_idempotency_and_conflicting_duplicate():
    db = connect()
    assert ingest(db, evt("one", "task_created", 1))
    assert not ingest(db, evt("one", "task_created", 1))
    with pytest.raises(DomainError):
        ingest(db, evt("one", "task_closed", 2))
    assert len(history(db, "T-1")) == 1


def test_evidence_and_graph_are_traceable():
    db = connect()
    ingest(db, evt("start", "task_created", 1))
    ingest(db, evt("confirmed", "driver_confirmed", 2))
    ingest(db, evt("paid", "payment_settled", 3))
    ingest(db, evt("closed", "task_closed", 4))
    report = evaluate(db, "T-1")
    assert {f["rule_id"] for f in report["findings"]} == {"CUSTODY_BEFORE_CLOSURE", "PAYMENT_WITHOUT_CUSTODY"}
    assert "confirmed" in report["findings"][-1]["evidence_event_ids"]
    graph = operational_graph(report)
    assert any(e["label"] == "SUPPORTED_BY" for e in graph["edges"])


def test_isolation_and_validation():
    db = connect()
    ingest(db, evt("a", "task_created", 1, "A"))
    assert evaluate(db, "B")["event_count"] == 0
    with pytest.raises(DomainError):
        ingest(db, {**evt("naive", "task_created", 1), "occurred_at": "2026-10-01T10:00:00"})
    with pytest.raises(DomainError):
        ingest(db, evt("wrong", "unknown", 1))


def test_persistence(tmp_path):
    path = tmp_path / "ops.sqlite"
    db = connect(path)
    ingest(db, evt("a", "task_created", 1))
    db.close()
    reopened = connect(path)
    assert evaluate(reopened, "T-1")["event_count"] == 1
