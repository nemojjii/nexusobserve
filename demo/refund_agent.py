"""Refund demo agent — shows how Nexus captures a decision with discarded alternatives.

A customer-support agent decides how to handle a refund request. It enumerates
four candidate actions, scores them, picks one, and records the decision —
chosen + discarded alternatives + replay payload — via the Nexus SDK.

Run from the repo root:

    python demo/refund_agent.py

Optionally ship to a running server:

    NEXUS_SERVER=http://localhost:8000 python demo/refund_agent.py
"""

from __future__ import annotations

import os
import sys
import time
from typing import Optional
from uuid import uuid4

# Make the SDK and shared contracts importable from a plain checkout.
_here = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.abspath(os.path.join(_here, ".."))
for p in (_repo_root, os.path.join(_repo_root, "packages", "sdk")):
    if p not in sys.path:
        sys.path.insert(0, p)

from contracts.schema import DecisionRecord  # noqa: E402
from nexus_sdk import record_decision  # noqa: E402

# Default order used by main() — override in tests via run_agent().
DEFAULT_ORDER = {
    "order_id": "ORD-1042",
    "amount": 500.00,
    "customer_tier": "gold",
    "reason_code": "item_not_as_described",
}


def decide_refund(order: dict) -> dict:
    """Score four candidate actions and pick the best one.

    Candidates
    ----------
    full_refund   $500  — keeps the customer, costs most
    partial_refund $200  — middle ground
    escalate       $120  — route to a senior agent, lower immediate cost
    deny+coupon    $30   — deny refund but issue a $30 coupon

    Policy: gold-tier customers always get a full refund.

    Returns
    -------
    dict with keys: ``chosen``, ``alternatives``, ``replay_payload``.
    The ``replay_payload`` follows the multi-tool list convention so the replay
    engine can REPLAYED query tools and SIMULATE side-effect tools.
    """
    amount = order["amount"]
    tier = order["customer_tier"]

    # cost = expected monetary cost to the business of taking the action.
    candidates = [
        {"action": "full_refund",   "cost": float(amount),       "reason": "retains gold customer"},
        {"action": "partial_refund", "cost": 200.0,               "reason": "splits the difference"},
        {"action": "escalate",       "cost": 120.0,               "reason": "senior agent handles it"},
        {"action": "deny+coupon",    "cost": 30.0,                "reason": "cheapest; issue $30 coupon"},
    ]

    chosen_action = "full_refund" if tier == "gold" else "partial_refund"
    chosen = next(c for c in candidates if c["action"] == chosen_action)
    alternatives = [c for c in candidates if c["action"] != chosen_action]

    replay_payload = {
        "tools": [
            # Query tool: looked up the order — return recorded outputs on replay.
            {
                "name": "order_lookup",
                "type": "query",
                "inputs": {"order_id": order["order_id"]},
                "outputs": {
                    "status": "delivered",
                    "amount": float(amount),
                    "days_since_delivery": 2,
                    "customer_tier": tier,
                },
            },
            # Side-effect tool: would execute the actual refund — must be SIMULATED.
            {
                "name": "refund_execute",
                "type": "side_effect",
                "inputs": {
                    "order_id": order["order_id"],
                    "amount": float(amount),
                    "action": chosen_action,
                },
            },
        ],
        "policy": f"gold->full_refund (tier={tier})",
    }
    return {"chosen": chosen, "alternatives": alternatives, "replay_payload": replay_payload}


def run_agent(
    order: Optional[dict] = None,
    run_id: Optional[str] = None,
    server_url: Optional[str] = None,
) -> DecisionRecord:
    """Run the refund agent, record the decision, and return the DecisionRecord.

    This is the importable entry point used by tests and the e2e script.
    ``main()`` is a thin wrapper around this.
    """
    order = order or DEFAULT_ORDER
    run_id = run_id or f"refund-run-{uuid4().hex[:8]}"

    t0 = time.perf_counter()
    result = decide_refund(order)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    return record_decision(
        run_id=run_id,
        context=order,
        chosen=result["chosen"],
        alternatives=result["alternatives"],
        latency_ms=latency_ms,
        replay_payload=result["replay_payload"],
        server_url=server_url,
    )


def main() -> None:
    server_url = os.environ.get("NEXUS_SERVER")
    record = run_agent(server_url=server_url)

    print(f"run_id      : {record.run_id}")
    print(f"decision_id : {record.decision_id}")
    print(f"chosen      : {record.chosen['action']} (cost=${record.chosen['cost']:.2f})")
    print("opportunity costs of discarded alternatives:")
    for opp in record.opportunity_costs():
        sign = "+" if (opp["opportunity_cost"] or 0) >= 0 else ""
        print(f"  - {opp['action']:16s}  cost=${opp['cost']:<8.2f}  "
              f"opp_cost={sign}{opp['opportunity_cost']:.2f}")
    if server_url:
        print(f"\nshipped → {server_url}/decisions")
    else:
        print("\n(set NEXUS_SERVER to ship this record to a running Nexus server)")


if __name__ == "__main__":
    main()
