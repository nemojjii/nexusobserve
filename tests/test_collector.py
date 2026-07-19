"""Tests for the Nexus Collector API (FastAPI TestClient — no live server).

Skipped automatically when ``nexus_collector`` or ``fastapi`` are not installed
(e.g. when only ``pip install -e nexusobserve`` was run).
"""

import json
import sys
import os

import pytest

# Skip the entire module if collector stack is not installed.
pytest.importorskip("fastapi",        reason="fastapi not installed — skipping collector tests")
pytest.importorskip("nexus_collector", reason="nexus_collector not installed — skipping collector tests")

# Ensure repo root on path for contracts import bootstrapped by collector.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from fastapi.testclient import TestClient

from contracts.schema import DecisionRecord
from nexus_collector.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _refund_record(run_id: str = "test-run-01") -> DecisionRecord:
    return DecisionRecord(
        run_id=run_id,
        context={"order_id": "ORD-9999", "amount": 500, "customer_tier": "gold"},
        chosen={"action": "full_refund", "cost": 500.0, "reason": "gold policy"},
        alternatives=[
            {"action": "escalate",    "cost": 120.0},
            {"action": "deny+coupon", "cost":  30.0},
        ],
        latency_ms=18.4,
        replay_payload={
            "tools": [
                {
                    "name": "order_lookup",
                    "type": "query",
                    "inputs":  {"order_id": "ORD-9999"},
                    "outputs": {"status": "delivered", "days_since": 2},
                },
                {
                    "name": "refund_execute",
                    "type": "side_effect",
                    "inputs": {"order_id": "ORD-9999", "amount": 500},
                },
            ],
        },
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_post_and_retrieve_decision():
    rec = _refund_record(run_id="retrieve-run")
    with TestClient(app) as client:
        post = client.post(
            "/decisions",
            content=rec.to_json(),
            headers={"Content-Type": "application/json"},
        )
        assert post.status_code == 200, post.text

        get = client.get(f"/runs/retrieve-run/decisions")
        assert get.status_code == 200
        body = get.json()
        assert body["count"] == 1
        assert body["decisions"][0]["decision_id"] == rec.decision_id
        assert len(body["decisions"][0]["alternatives"]) == 2


def test_replay_cost_delta():
    rec = _refund_record(run_id="replay-run")
    with TestClient(app) as client:
        client.post(
            "/decisions",
            content=rec.to_json(),
            headers={"Content-Type": "application/json"},
        )
        resp = client.post(
            "/replay",
            content=json.dumps({"decision_id": rec.decision_id, "alternative_action": "escalate"}),
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["cost_delta"] == 380.0, f"expected 380.0 got {result['cost_delta']}"
    assert result["side_effects_executed"] == 0


def test_replay_simulated_side_effect():
    rec = _refund_record(run_id="simulated-run")
    with TestClient(app) as client:
        client.post("/decisions", content=rec.to_json(), headers={"Content-Type": "application/json"})
        resp = client.post(
            "/replay",
            content=json.dumps({"decision_id": rec.decision_id, "alternative_action": "escalate"}),
            headers={"Content-Type": "application/json"},
        )
    tools = {t["tool"]: t for t in resp.json()["replayed_tools"]}
    assert tools["order_lookup"]["status"]  == "REPLAYED"
    assert tools["refund_execute"]["status"] == "SIMULATED"


def test_replay_unknown_alternative_returns_error():
    # replay.py raises ValueError for unknown action → main.py maps that to 422
    rec = _refund_record(run_id="422-run")
    with TestClient(app) as client:
        client.post("/decisions", content=rec.to_json(), headers={"Content-Type": "application/json"})
        resp = client.post(
            "/replay",
            content=json.dumps({"decision_id": rec.decision_id, "alternative_action": "no_such_action"}),
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 422


def test_list_runs():
    with TestClient(app) as client:
        for run_id in ("run-a", "run-b"):
            rec = _refund_record(run_id=run_id)
            client.post("/decisions", content=rec.to_json(), headers={"Content-Type": "application/json"})
        resp = client.get("/runs")
    assert resp.status_code == 200
    runs = resp.json()["runs"]
    assert "run-a" in runs
    assert "run-b" in runs


def test_post_decision_duplicate_id_is_idempotent():
    rec = _refund_record(run_id="dup-run")
    with TestClient(app) as client:
        r1 = client.post("/decisions", content=rec.to_json(), headers={"Content-Type": "application/json"})
        r2 = client.post("/decisions", content=rec.to_json(), headers={"Content-Type": "application/json"})
        get = client.get("/runs/dup-run/decisions")
    assert r1.status_code == 200
    assert r2.status_code == 200
    # INSERT OR REPLACE — still exactly one record
    assert get.json()["count"] == 1
