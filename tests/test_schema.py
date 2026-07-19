"""Tests for contracts/schema.py — DecisionRecord SSOT."""

import json
import sys, os

# Ensure repo root is on path for `contracts` import.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from contracts.schema import DecisionRecord, from_dict, from_json


def _sample() -> DecisionRecord:
    return DecisionRecord(
        run_id="r1",
        context={"order_id": "ORD-1042", "amount": 500},
        chosen={"action": "full_refund", "cost": 500.0},
        alternatives=[
            {"action": "escalate",    "cost": 120.0},
            {"action": "deny+coupon", "cost":  30.0},
        ],
        latency_ms=12.3,
    )


def test_roundtrip_json():
    rec = _sample()
    rec2 = from_json(rec.to_json())
    assert rec2.run_id == rec.run_id
    assert rec2.decision_id == rec.decision_id
    assert rec2.chosen == rec.chosen
    assert rec2.alternatives == rec.alternatives


def test_roundtrip_dict():
    rec = _sample()
    rec2 = from_dict(rec.to_dict())
    assert rec2.decision_id == rec.decision_id
    assert rec2.latency_ms == rec.latency_ms


def test_decision_id_auto_generated():
    r1 = _sample()
    r2 = _sample()
    assert r1.decision_id != r2.decision_id


def test_opportunity_costs():
    rec = _sample()
    opp = {o["action"]: o["opportunity_cost"] for o in rec.opportunity_costs()}
    # alt.cost - chosen.cost
    assert opp["escalate"]    == 120.0 - 500.0   # -380
    assert opp["deny+coupon"] ==  30.0 - 500.0   # -470


def test_schema_version_present():
    rec = _sample()
    d = rec.to_dict()
    assert "schema_version" in d
    assert isinstance(d["schema_version"], int)
