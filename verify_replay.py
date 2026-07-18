"""Verification script for POST /replay.

Tests the replay engine via FastAPI's TestClient (no live server needed).

Scenario:
  - Agent chose "full_refund" at cost $500.
  - Discarded alternative "escalate" at cost $120.
  - replay_payload has one query tool (order_lookup) and one side-effect tool
    (refund_execute).

Assertions:
  - cost_delta == 380  (500 - 120)
  - side_effects_executed == 0
"""

from __future__ import annotations

import json
import os
import sys

# Bootstrap monorepo root so `contracts` and server packages are importable.
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(_here, "packages", "server"))

os.environ["NEXUS_DB_PATH"] = ":memory:"  # in-memory DB — no leftover files

from contracts.schema import DecisionRecord  # noqa: E402
from nexus_server.main import app  # noqa: E402

# FastAPI TestClient uses httpx under the hood; fall back to a direct function
# call if httpx is not installed.
try:
    from fastapi.testclient import TestClient
    _USE_HTTP = True
except ImportError:  # pragma: no cover
    _USE_HTTP = False


# --------------------------------------------------------------------------- #
# Build the demo decision record
# --------------------------------------------------------------------------- #

DEMO_RECORD = DecisionRecord(
    run_id="verify-run-01",
    context={"order_id": "ORD-9999", "amount": 500, "customer_tier": "silver"},
    chosen={"action": "full_refund", "cost": 500, "reason": "policy override"},
    alternatives=[
        {"action": "escalate", "cost": 120, "reason": "route to senior agent"},
        {"action": "deny",     "cost": 0,   "reason": "no eligible refund"},
    ],
    latency_ms=18.4,
    replay_payload={
        "tools": [
            {
                "name": "order_lookup",
                "type": "query",
                "inputs":  {"order_id": "ORD-9999"},
                "outputs": {"status": "delivered", "days_since": 12},
            },
            {
                "name": "refund_execute",
                "type": "side_effect",
                "inputs": {"order_id": "ORD-9999", "amount": 500},
            },
        ],
        "processing_delay_ms": 42,
    },
)


def run_via_http() -> dict:
    # Use as context manager so FastAPI's startup event fires (calls init_db()).
    with TestClient(app) as client:
        # 1. Store the decision.
        store_resp = client.post(
            "/decisions",
            content=DEMO_RECORD.to_json(),
            headers={"Content-Type": "application/json"},
        )
        assert store_resp.status_code == 200, f"store failed: {store_resp.text}"

        # 2. Replay the "escalate" alternative.
        replay_resp = client.post(
            "/replay",
            content=json.dumps(
                {"decision_id": DEMO_RECORD.decision_id, "alternative_action": "escalate"}
            ),
            headers={"Content-Type": "application/json"},
        )
        assert replay_resp.status_code == 200, f"replay failed: {replay_resp.text}"
        return replay_resp.json()


def run_direct() -> dict:
    """Bypass HTTP entirely — test the replay engine function directly."""
    from nexus_server.replay import replay_decision
    return replay_decision(DEMO_RECORD, "escalate")


def main() -> None:
    if _USE_HTTP:
        print("running via FastAPI TestClient (HTTP)…")
        result = run_via_http()
    else:
        print("httpx not installed — testing replay engine directly…")
        result = run_direct()

    print(json.dumps(result, indent=2, ensure_ascii=False))

    # --- assertions -------------------------------------------------------
    cost_delta = result["cost_delta"]
    assert cost_delta == 380, (
        f"FAIL: expected cost_delta=380, got {cost_delta!r}"
    )
    print(f"\nPASS: cost_delta == {cost_delta}")

    side_fx = result["side_effects_executed"]
    assert side_fx == 0, (
        f"FAIL: expected side_effects_executed=0, got {side_fx!r}"
    )
    print(f"PASS: side_effects_executed == {side_fx}")

    # refund_execute must appear as SIMULATED, not REPLAYED.
    tools = result["replayed_tools"]
    sim = [t for t in tools if t.get("tool") == "refund_execute"]
    assert sim and sim[0]["status"] == "SIMULATED", (
        f"FAIL: refund_execute should be SIMULATED, got {sim}"
    )
    print("PASS: refund_execute is SIMULATED (not executed)")

    # order_lookup must appear as REPLAYED (recorded outputs returned).
    qry = [t for t in tools if t.get("tool") == "order_lookup"]
    assert qry and qry[0]["status"] == "REPLAYED", (
        f"FAIL: order_lookup should be REPLAYED, got {qry}"
    )
    print("PASS: order_lookup is REPLAYED (recorded outputs)")

    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()
