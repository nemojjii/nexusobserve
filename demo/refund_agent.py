"""Refund demo agent — narrative stub showing how Nexus captures a decision.

A tiny "customer support" agent decides how to handle a refund request. It
enumerates candidate actions (full refund / partial refund / deny), scores them,
picks one, and records the decision — chosen + discarded alternatives — via the
Nexus SDK.

Run from the repo root:

    python demo/refund_agent.py

Optionally ship to a running server:

    NEXUS_SERVER=http://localhost:8000 python demo/refund_agent.py
"""

from __future__ import annotations

import os
import sys
import time
from uuid import uuid4

# Make the SDK and shared contracts importable from a plain checkout.
_here = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.abspath(os.path.join(_here, ".."))
for p in (_repo_root, os.path.join(_repo_root, "packages", "sdk")):
    if p not in sys.path:
        sys.path.insert(0, p)

from nexus_sdk import record_decision  # noqa: E402


def decide_refund(order: dict) -> dict:
    """Score candidate actions for a refund request and pick the best one.

    Returns a dict with `chosen`, `alternatives`, and `replay_payload`.
    """
    amount = order["amount"]
    tier = order["customer_tier"]

    # `cost` here = expected cost to the business of taking the action.
    # A real agent would call tools / an LLM; this is a deterministic stub.
    candidates = [
        {"action": "full_refund", "cost": amount,
         "reason": "keeps a high-value customer happy"},
        {"action": "partial_refund", "cost": round(amount * 0.5, 2),
         "reason": "splits the difference"},
        {"action": "deny", "cost": 0.0,
         "reason": "cheapest now, risks churn"},
    ]

    # Simple policy: gold customers get full refunds; otherwise partial.
    chosen_action = "full_refund" if tier == "gold" else "partial_refund"
    chosen = next(c for c in candidates if c["action"] == chosen_action)
    alternatives = [c for c in candidates if c["action"] != chosen_action]

    replay_payload = {
        "tool": "policy_engine.decide_refund",
        "inputs": order,
        "candidates": candidates,
        "policy": "gold->full_refund else partial_refund",
    }
    return {"chosen": chosen, "alternatives": alternatives, "replay_payload": replay_payload}


def main() -> None:
    run_id = f"refund-run-{uuid4().hex[:8]}"
    server_url = os.environ.get("NEXUS_SERVER")  # optional

    order = {
        "order_id": "ORD-1042",
        "amount": 120.00,
        "customer_tier": "gold",
        "reason_code": "item_not_as_described",
    }

    t0 = time.perf_counter()
    result = decide_refund(order)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    record = record_decision(
        run_id=run_id,
        context=order,
        chosen=result["chosen"],
        alternatives=result["alternatives"],
        latency_ms=latency_ms,
        replay_payload=result["replay_payload"],
        server_url=server_url,
    )

    print(f"run_id      : {record.run_id}")
    print(f"decision_id : {record.decision_id}")
    print(f"chosen      : {record.chosen['action']} (cost={record.chosen['cost']})")
    print("opportunity costs of discarded alternatives:")
    for opp in record.opportunity_costs():
        print(f"  - {opp['action']:16s} cost={opp['cost']:<8} "
              f"opportunity_cost={opp['opportunity_cost']}")
    if server_url:
        print(f"\nshipped to {server_url}/decisions")
    else:
        print("\n(set NEXUS_SERVER to ship this record to a running Nexus server)")


if __name__ == "__main__":
    main()
