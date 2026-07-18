# nexus-sdk

Instrument an AI agent so every branching decision is captured as a
`DecisionRecord` — the chosen option **plus the discarded alternatives** and a
replay payload.

```bash
pip install -e packages/sdk   # needs pip >= 21.3 (PEP 660 editable installs)
```

```python
from nexus_sdk import record_decision

rec = record_decision(
    run_id="run-123",
    context={"order_id": "A1", "amount": 100, "customer_tier": "gold"},
    chosen={"action": "full_refund", "cost": 100},
    alternatives=[
        {"action": "partial_refund", "cost": 50},
        {"action": "deny", "cost": 0},
    ],
    latency_ms=12.3,
    replay_payload={"tool": "refund_api", "args": {...}},
    server_url="http://localhost:8000",  # optional; POSTs the record
)
```

The record schema is defined once in the repo-root `contracts/schema.py` and
shared by every layer.
