# nexusobserve

> Instrument AI agents to capture **chosen + discarded alternatives + opportunity cost** at every decision point. Then replay any discarded alternative to diff the outcome — without executing side-effects.

```bash
pip install nexusobserve
```

## Quickstart

```python
from nexusobserve import record_decision

rec = record_decision(
    run_id="run-123",
    context={"order_id": "ORD-1042", "amount": 500, "customer_tier": "gold"},
    chosen={"action": "full_refund", "cost": 500},
    alternatives=[
        {"action": "escalate",       "cost": 120},
        {"action": "partial_refund", "cost": 200},
        {"action": "deny+coupon",    "cost": 30},
    ],
    latency_ms=12.3,
    replay_payload={
        "tools": [
            {"name": "order_lookup",  "type": "query",       "inputs": {...}, "outputs": {...}},
            {"name": "refund_execute","type": "side_effect",  "inputs": {...}},
        ]
    },
    server_url="http://localhost:8000",  # optional — POSTs to Nexus Collector
)

# Opportunity cost of each discarded alternative (pure math, no LLM)
for opp in rec.opportunity_costs():
    print(opp)  # {"action": "escalate", "cost": 120, "opportunity_cost": -380}
```

## How it works

1. **SDK** (`nexusobserve`) — call `record_decision()` inside the agent.
2. **Collector** (`nexus-collector`) — FastAPI + SQLite; receives and stores records.
3. **Dashboard Lite** — React force-graph; click a discarded alternative → see the replay diff.

The `contracts/schema.py` `DecisionRecord` is the single source of truth shared by all three layers.

## replay_payload conventions

```python
# Multi-tool list (preferred)
replay_payload = {
    "tools": [
        {"name": "lookup",  "type": "query",       "inputs": {...}, "outputs": {...}},
        {"name": "execute", "type": "side_effect",  "inputs": {...}},
    ]
}

# Single-tool shorthand (backward-compat)
replay_payload = {"tool": "policy_engine", "inputs": {...}, "outputs": {...}}
```

Side-effect tools are **never re-executed** during replay — they are marked `SIMULATED`.
Query tools return their recorded `outputs`.

## License

MIT
